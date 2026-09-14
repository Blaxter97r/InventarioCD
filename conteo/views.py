from functools import wraps
from io import BytesIO
from decimal import Decimal, ROUND_HALF_UP, localcontext
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, IntegerField, Prefetch, Q
from django.db.models.functions import Cast
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from django.utils import timezone

from archivos.models import CostoProducto, Linea

from .forms import DiferenciasUploadForm
from .models import CargaDiferencias, Diferencia, InicioReconteoBodega
from .services import DifferenceImportError, import_differences
from .progress import build_progress_dashboard
from .recount_reports import WAREHOUSES, attach_warehouse_options, build_recount_pdf


def admin_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not (
            request.user.is_superuser
            or request.user.groups.filter(name="Admin").exists()
        ):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped


def manager_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not (
            request.user.is_superuser
            or request.user.groups.filter(name__in=("Admin", "Gerente")).exists()
        ):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped


def _ordered_lines():
    return Linea.objects.annotate(
        orden_numerico=Cast("nlinea", IntegerField())
    ).order_by("orden_numerico", "nlinea")


@login_required
def differences_index_view(request):
    selected_line = request.GET.get("linea", "").strip()
    loads = CargaDiferencias.objects.select_related("linea", "cargado_por")
    if selected_line:
        loads = loads.filter(linea_id=selected_line)
    latest_load = loads.first()

    context = {
        "selected_line": selected_line,
        "line_choices": _ordered_lines(),
        "latest_load": latest_load,
        "recent_loads": CargaDiferencias.objects.select_related("linea", "cargado_por")[:6],
        "total_loads": CargaDiferencias.objects.count(),
        "total_differences": Diferencia.objects.count(),
    }
    return render(request, "conteo/differences_index.html", context)


@admin_required
def differences_upload_view(request):
    form = DiferenciasUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            load = import_differences(
                form.cleaned_data["archivo"],
                form.cleaned_data["linea"],
                request.user,
                form.cleaned_data["archivo_as400"],
            )
        except DifferenceImportError as error:
            form.add_error("archivo", str(error))
        else:
            messages.success(
                request,
                f"Se cargaron {load.total_registros} diferencias para la línea "
                f"{load.linea.nlinea} · {load.linea.descripcion}.",
            )
            target = reverse("conteo:differences_index")
            return redirect(f"{target}?{urlencode({'linea': load.linea_id})}")
    return render(request, "conteo/differences_upload.html", {"form": form})


@admin_required
def differences_template_view(request):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Diferencias"
    headers = (
        "linea",
        "sublinea",
        "item",
        "codigo",
        "descripcion",
        "ultimo conteo",
        "existencia",
        "Diferencia",
        "Ubicación 1",
        "Ubicación 2",
        "Ubicación 3",
        "Ubicación 4",
        "Fecha Geracion",
        "Hora Generación",
    )
    sheet.append(headers)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = "A1:N1"
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="087F76")
        cell.alignment = Alignment(horizontal="center")
    widths = (14, 15, 14, 22, 38, 18, 15, 15, 20, 20, 20, 20, 20, 18)
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[chr(64 + index)].width = width

    instructions = workbook.create_sheet("Instrucciones", 0)
    instructions.append(["FORMATO PARA CARGAR DIFERENCIAS POR LÍNEA"])
    instructions.append(["Selecciona en la plataforma la misma línea indicada en todas las filas."])
    instructions.append(["No cambies ni elimines los encabezados de la hoja Diferencias."])
    instructions.append(["Ubicación 1 a Ubicación 4 pueden quedar vacías."])
    instructions.append(["Fecha sugerida: DD/MM/AAAA. Hora sugerida: HH:MM:SS."])
    instructions.column_dimensions["A"].width = 90

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="plantilla_diferencias_por_linea.xlsx"'
    return response


@manager_required
def pending_queue_view(request):
    pending_loads = (
        CargaDiferencias.objects.filter(estado=CargaDiferencias.Estado.PENDIENTE)
        .select_related("linea", "cargado_por")
        .annotate(
            candidate_count=Count(
                "diferencias",
                filter=~Q(diferencias__diferencia=0),
            )
        )
        .order_by("fecha_carga")
    )
    return render(
        request,
        "conteo/pending_queue.html",
        {
            "pending_loads": pending_loads,
            "pending_total": pending_loads.count(),
        },
    )


@manager_required
def pending_codes_view(request, pk):
    load = get_object_or_404(
        CargaDiferencias.objects.select_related("linea"),
        pk=pk,
        estado=CargaDiferencias.Estado.PENDIENTE,
    )
    codes = list(
        load.diferencias.exclude(diferencia=0)
        .order_by("sublinea", "codigo")
        .values(
            "id",
            "sublinea",
            "codigo",
            "ultimo_conteo",
            "existencia",
            "diferencia",
            "ubicacion_1",
            "ubicacion_2",
            "ubicacion_3",
            "ubicacion_4",
        )
    )
    costs_by_code = {
        codigo.upper(): costo
        for codigo, costo in CostoProducto.objects.filter(
            codigo__in={code["codigo"].upper() for code in codes}
        ).values_list("codigo", "costo")
    }
    for code in codes:
        difference = code["diferencia"]
        for field in ("ultimo_conteo", "existencia", "diferencia"):
            code[field] = format(
                code[field].quantize(Decimal("1"), rounding=ROUND_HALF_UP),
                "f",
            )
        cost = costs_by_code.get(code["codigo"].upper())
        if cost is None:
            code["costo"] = None
            code["costo_total"] = None
        else:
            with localcontext() as context:
                context.prec = 50
                total = (cost * difference).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                )
            code["costo"] = format(cost, ".2f")
            code["costo_total"] = format(total, ".2f")
    return JsonResponse(
        {
            "id": load.pk,
            "linea": f"Línea {load.linea.nlinea} · {load.linea.descripcion}",
            "reconteo": load.numero_reconteo,
            "archivo": load.archivo_nombre,
            "codes": codes,
        }
    )


@manager_required
def select_recount_codes_view(request, pk):
    if request.method != "POST":
        raise Http404
    with transaction.atomic():
        load = get_object_or_404(
            CargaDiferencias.objects.select_for_update().select_related("linea"),
            pk=pk,
        )
        if load.estado != CargaDiferencias.Estado.PENDIENTE:
            messages.info(request, "Los códigos de este archivo ya fueron seleccionados.")
            return redirect("conteo:pending_queue")

        candidates = load.diferencias.exclude(diferencia=0)
        if request.POST.get("select_all") == "1":
            selected = candidates
        else:
            selected_ids = request.POST.getlist("codes")
            selected = candidates.filter(pk__in=selected_ids)
        if not selected.exists():
            messages.error(request, "Selecciona al menos un código antes de guardar.")
            return redirect("conteo:pending_queue")

        load.diferencias.update(seleccionada=False)
        selected.update(seleccionada=True)
        load.estado = CargaDiferencias.Estado.RECONTEO
        load.seleccionado_por = request.user
        load.fecha_seleccion = timezone.now()
        load.save(update_fields=("estado", "seleccionado_por", "fecha_seleccion"))

    messages.success(
        request,
        f"Se enviaron {selected.count()} códigos de la línea {load.linea.nlinea} "
        "a la bandeja de Reconteos.",
    )
    return redirect("conteo:recounts")


@manager_required
def finalize_line_view(request, pk):
    if request.method != "POST":
        raise Http404

    with transaction.atomic():
        load = get_object_or_404(
            CargaDiferencias.objects.select_for_update().select_related("linea"),
            pk=pk,
        )
        if load.estado != CargaDiferencias.Estado.PENDIENTE:
            messages.info(request, "Este archivo ya fue procesado anteriormente.")
            return redirect("conteo:pending_queue")

        load.diferencias.update(seleccionada=False)
        load.estado = CargaDiferencias.Estado.FINALIZADO
        load.finalizado_por = request.user
        load.fecha_finalizacion = timezone.now()
        load.save(update_fields=("estado", "finalizado_por", "fecha_finalizacion"))

    messages.success(
        request,
        f"La línea {load.linea.nlinea} fue finalizada sin códigos para reconteo.",
    )
    return redirect("conteo:line_summary")


@admin_required
def delete_pending_recount_view(request, pk):
    if request.method != "POST":
        raise Http404

    with transaction.atomic():
        load = get_object_or_404(
            CargaDiferencias.objects.select_for_update().select_related("linea"),
            pk=pk,
        )
        if load.estado != CargaDiferencias.Estado.PENDIENTE:
            messages.error(request, "Solo se pueden eliminar reconteos pendientes.")
            return redirect("conteo:pending_queue")

        line_number = load.linea.nlinea
        recount_number = load.numero_reconteo
        file_name = load.archivo_original.name
        file_storage = load.archivo_original.storage
        as400_file_name = load.archivo_as400.name
        as400_file_storage = load.archivo_as400.storage
        load.delete()
        if file_name:
            transaction.on_commit(lambda: file_storage.delete(file_name))
        if as400_file_name:
            transaction.on_commit(lambda: as400_file_storage.delete(as400_file_name))

    messages.success(
        request,
        f"Reconteo #{recount_number} de la línea {line_number} eliminado correctamente.",
    )
    return redirect("conteo:pending_queue")


@manager_required
def download_recount_view(request, pk):
    load = get_object_or_404(CargaDiferencias, pk=pk)
    if not load.archivo_original:
        raise Http404("El archivo original no está disponible.")
    try:
        file_handle = load.archivo_original.open("rb")
    except FileNotFoundError as error:
        raise Http404("El archivo original no está disponible.") from error
    return FileResponse(file_handle, as_attachment=True, filename=load.archivo_nombre)


@login_required
def recounts_view(request):
    selected_codes = Diferencia.objects.filter(seleccionada=True).order_by("sublinea", "codigo")
    pending_lines = CargaDiferencias.objects.filter(
        estado=CargaDiferencias.Estado.PENDIENTE
    ).values("linea_id")
    loads = (
        CargaDiferencias.objects.filter(estado=CargaDiferencias.Estado.RECONTEO)
        .exclude(linea_id__in=pending_lines)
        .select_related("linea", "seleccionado_por")
        .prefetch_related(Prefetch("diferencias", queryset=selected_codes, to_attr="codigos_reconteo"))
        .prefetch_related("inicios_bodega")
        .annotate(selected_count=Count("diferencias", filter=Q(diferencias__seleccionada=True)))
        .order_by("linea_id", "-fecha_seleccion", "-pk")
    )
    latest_by_line = {}
    for load in loads:
        latest_by_line.setdefault(load.linea_id, load)
    recounts = sorted(
        latest_by_line.values(),
        key=lambda load: (
            int(load.linea.nlinea) if load.linea.nlinea.isdigit() else 10**9,
            load.linea.nlinea,
        ),
    )
    attach_warehouse_options(recounts)
    for load in recounts:
        started = {item.bodega: item for item in load.inicios_bodega.all()}
        for option in load.warehouse_options:
            option["inicio"] = started.get(option["key"])
        load.finished_warehouse_labels = [
            option["label"] for option in load.warehouse_options
            if option["count"] and option["inicio"] and option["inicio"].fecha_fin
        ]
        load.remaining_warehouse_labels = [
            option["label"] for option in load.warehouse_options
            if option["count"] and not (option["inicio"] and option["inicio"].fecha_fin)
        ]
        load.all_assigned_finished = bool(load.finished_warehouse_labels) and not (
            load.remaining_warehouse_labels or load.unclassified_codes
        )
    return render(
        request,
        "conteo/recounts.html",
        {"recounts": recounts, "recount_total": len(recounts)},
    )


@login_required
def start_recount_warehouse_view(request, pk, warehouse):
    if request.method != "POST" or warehouse not in WAREHOUSES:
        raise Http404
    with transaction.atomic():
        load = get_object_or_404(
            CargaDiferencias.objects.select_for_update().select_related("linea"),
            pk=pk,
            estado=CargaDiferencias.Estado.RECONTEO,
        )
        latest = CargaDiferencias.objects.filter(linea=load.linea).first()
        if latest.pk != load.pk:
            messages.error(request, "Este reconteo ya no es el vigente de la línea.")
            return redirect("conteo:recounts")
        load.codigos_reconteo = list(load.diferencias.filter(seleccionada=True))
        attach_warehouse_options([load])
        option = next(item for item in load.warehouse_options if item["key"] == warehouse)
        if not option["count"]:
            messages.error(request, "No hay códigos asignados a esa bodega para este reconteo.")
            return redirect("conteo:recounts")
        _, created = InicioReconteoBodega.objects.get_or_create(
            carga=load, bodega=warehouse, defaults={"iniciado_por": request.user}
        )
    if created:
        messages.success(request, f"Reconteo de {WAREHOUSES[warehouse]} iniciado.")
    else:
        messages.info(request, f"El reconteo de {WAREHOUSES[warehouse]} ya estaba iniciado.")
    return redirect("conteo:recounts")


@login_required
def finish_recount_warehouse_view(request, pk, warehouse):
    if request.method != "POST" or warehouse not in WAREHOUSES:
        raise Http404
    with transaction.atomic():
        load = get_object_or_404(
            CargaDiferencias.objects.select_for_update().select_related("linea"),
            pk=pk, estado=CargaDiferencias.Estado.RECONTEO,
        )
        latest = CargaDiferencias.objects.filter(linea=load.linea).first()
        if latest.pk != load.pk:
            messages.error(request, "Este reconteo ya no es el vigente de la línea.")
            return redirect("conteo:recounts")
        progress = InicioReconteoBodega.objects.select_for_update().filter(
            carga=load, bodega=warehouse
        ).first()
        if progress is None:
            messages.error(request, f"Primero inicia el reconteo de {WAREHOUSES[warehouse]}.")
            return redirect("conteo:recounts")
        if progress.fecha_fin:
            messages.info(request, f"El reconteo de {WAREHOUSES[warehouse]} ya estaba finalizado.")
            return redirect("conteo:recounts")
        progress.finalizado_por = request.user
        progress.fecha_fin = timezone.now()
        progress.save(update_fields=("finalizado_por", "fecha_fin"))
    messages.success(request, f"Reconteo de {WAREHOUSES[warehouse]} finalizado.")
    return redirect("conteo:recounts")


@login_required
def recount_warehouse_report_view(request, pk, warehouse):
    if warehouse not in WAREHOUSES:
        raise Http404("La bodega solicitada no existe.")
    load = get_object_or_404(
        CargaDiferencias.objects.select_related("linea", "seleccionado_por"),
        pk=pk,
        estado=CargaDiferencias.Estado.RECONTEO,
    )
    report = build_recount_pdf(load, warehouse)
    filename = (
        f"reconteo_linea_{load.linea.nlinea}_{warehouse}_"
        f"{load.numero_reconteo}.pdf"
    )
    response = HttpResponse(
        report,
        content_type="application/pdf",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def line_summary_view(request):
    status_filters = (
        ("PTE_CARGA", "Pte carga"),
        ("PTE_GERENCIA", "Pte revisión Gerencia"),
        ("PTE_INICIAR", "Pte iniciar reconteo"),
        ("EN_PROCESO", "En proceso de reconteo"),
        ("RECONTEO_TERMINADO", "Reconteo terminado"),
        ("FINALIZADA", "Finalizada"),
    )
    selected_status = request.GET.get("estado", "").strip().upper()
    if selected_status not in dict(status_filters):
        selected_status = ""
    recount_history = (
        CargaDiferencias.objects.all()
        .select_related("linea", "seleccionado_por")
        .prefetch_related("inicios_bodega")
        .order_by("-fecha_carga", "-pk")
    )
    lines = list(_ordered_lines().prefetch_related(
        Prefetch("cargas_diferencias", queryset=recount_history, to_attr="historial_reconteos")
    ))
    current_recounts = [
        line.historial_reconteos[0] for line in lines
        if line.historial_reconteos and line.historial_reconteos[0].estado == CargaDiferencias.Estado.RECONTEO
    ]
    codes_by_load = {load.pk: [] for load in current_recounts}
    for difference in Diferencia.objects.filter(
        carga_id__in=codes_by_load, seleccionada=True
    ).only("carga_id", "codigo"):
        codes_by_load[difference.carga_id].append(difference)
    for load in current_recounts:
        load.codigos_reconteo = codes_by_load[load.pk]
    attach_warehouse_options(current_recounts)
    summary = []
    status_counts = {
        "PTE_CARGA": 0,
        "PTE_GERENCIA": 0,
        "PTE_INICIAR": 0,
        "EN_PROCESO": 0,
        "RECONTEO_TERMINADO": 0,
        "FINALIZADA": 0,
    }
    for line in lines:
        latest = line.historial_reconteos[0] if line.historial_reconteos else None
        started = {}
        if latest is None:
            recount_number = None
            status_code = "PTE_CARGA"
            status_label = "Pte carga"
        elif latest.estado == CargaDiferencias.Estado.PENDIENTE:
            # La carga está esperando la decisión de Gerencia; todavía no
            # existe un nuevo reconteo que numerar.
            recount_number = latest.numero_reconteo - 1 if latest.numero_reconteo > 1 else None
            status_code = "PTE_GERENCIA"
            status_label = "Pte revisión Gerencia"
        elif latest.estado == CargaDiferencias.Estado.RECONTEO:
            # El número nace cuando Gerencia decide enviar códigos a reconteo.
            recount_number = latest.numero_reconteo
            started = {item.bodega: item for item in latest.inicios_bodega.all()}
            assigned = [option for option in latest.warehouse_options if option["count"]]
            finished = [option for option in assigned if started.get(option["key"]) and started[option["key"]].fecha_fin]
            remaining = [option for option in assigned if option not in finished]
            if assigned and len(finished) == len(assigned) and not latest.unclassified_codes:
                status_code = "RECONTEO_TERMINADO"
                status_label = "Reconteo terminado · pendiente nueva carga"
            elif finished:
                status_code = "EN_PROCESO"
                done_names = " y ".join(option["label"] for option in finished)
                remaining_names = " y ".join(option["label"] for option in remaining)
                status_label = f"Finalizó {done_names} · falta finalizar {remaining_names}" if remaining else f"Finalizó {done_names} · códigos sin bodega"
            elif started:
                status_code = "EN_PROCESO"
                if len(started) == 2:
                    status_label = "En proceso · Central y RANSA"
                else:
                    status_label = f"En proceso · {WAREHOUSES[next(iter(started))]}"
            else:
                status_code = "PTE_INICIAR"
                status_label = "Pte iniciar reconteo"
        else:
            # Si se finalizó la primera carga nunca existió un reconteo. En
            # ciclos posteriores se conserva el último que sí fue ejecutado.
            recount_number = latest.numero_reconteo - 1 if latest.numero_reconteo > 1 else None
            status_code = "FINALIZADA"
            status_label = "Finalizada"
        summary.append(
            {
                "line": line,
                "load": latest,
                "recount_number": recount_number,
                "status_code": status_code,
                "status_label": status_label,
                "last_progress_at": max((item.fecha_fin or item.fecha_inicio for item in started.values()), default=None),
            }
        )
        status_counts[status_code] += 1
    visible_summary = [item for item in summary if item["status_code"] == selected_status] if selected_status else summary
    return render(
        request,
        "conteo/line_summary.html",
        {
            "recount_summary": visible_summary,
            "line_total": len(summary),
            "filtered_total": len(visible_summary),
            "selected_status": selected_status,
            "selected_status_label": dict(status_filters).get(selected_status, "Todas las líneas"),
            "status_filters": status_filters,
            "status_counts": status_counts,
        },
    )


@login_required
def selected_codes_view(request):
    return redirect("conteo:recounts")


@admin_required
def reset_differences_view(request):
    confirmation_phrase = "REINICIAR DIFERENCIAS"
    if request.method == "POST":
        if request.POST.get("confirmacion", "").strip() != confirmation_phrase:
            messages.error(request, "Escribe REINICIAR DIFERENCIAS para confirmar.")
        else:
            with transaction.atomic():
                loads = list(
                    CargaDiferencias.objects.select_for_update().values_list(
                        "archivo_original", "archivo_as400"
                    )
                )
                CargaDiferencias.objects.all().delete()
                original_storage = CargaDiferencias._meta.get_field("archivo_original").storage
                as400_storage = CargaDiferencias._meta.get_field("archivo_as400").storage
                for original_name, as400_name in loads:
                    if original_name:
                        transaction.on_commit(
                            lambda name=original_name: original_storage.delete(name), robust=True
                        )
                    if as400_name:
                        transaction.on_commit(
                            lambda name=as400_name: as400_storage.delete(name), robust=True
                        )
            messages.success(
                request,
                f"Se reiniciaron {len(loads)} cargas de diferencias y sus estados de reconteo.",
            )
            return redirect("usuarios:inicio")
    return render(
        request,
        "conteo/reset_differences.html",
        {
            "load_count": CargaDiferencias.objects.count(),
            "difference_count": Diferencia.objects.count(),
            "warehouse_progress_count": InicioReconteoBodega.objects.count(),
            "confirmation_phrase": confirmation_phrase,
        },
    )


@login_required
def progress_general_view(request):
    context = build_progress_dashboard()
    return render(request, "conteo/progress_general.html", context)


@login_required
def progress_view(request):
    context = build_progress_dashboard(
        request.GET.get("piso", "").strip(),
        request.GET.get("bodega", "").strip(),
        request.GET.get("tipo", "").strip(),
    )
    return render(request, "conteo/progress.html", context)


@login_required
def pending_locations_download_view(request, floor):
    context = build_progress_dashboard(
        floor.strip(),
        request.GET.get("bodega", "").strip(),
        request.GET.get("tipo", "").strip(),
    )
    if context["selected_floor"] != floor.strip().upper():
        raise Http404("El piso solicitado no existe en el mapa del mezzanine.")

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = f"Pendientes {context['selected_floor']}"
    sheet.append(context["download_headers"])
    for row in context["pending_rows"]:
        sheet.append(row)

    sheet.freeze_panes = "A2"
    last_column = chr(64 + len(context["download_headers"]))
    sheet.auto_filter.ref = f"A1:{last_column}{max(sheet.max_row, 1)}"
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="087F76")
        cell.alignment = Alignment(horizontal="center")
    for column, width in zip(("A", "B", "C", "D", "E", "F"), (12, 14, 12, 14, 12, 24)):
        sheet.column_dimensions[column].width = width

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="ubicaciones_pendientes_{context["selected_type"].lower()}_{context["selected_floor"]}.xlsx"'
    )
    return response
