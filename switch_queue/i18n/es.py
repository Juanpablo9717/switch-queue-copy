"""Spanish translations (neutral Latin American)."""

TRANSLATIONS = {
    # ----- App / sections -----
    "app.title": "Switch Queue Copy",
    "section.source": "Origen",
    "section.dest": "Destino",
    "section.queue": "Cola",
    "section.appearance": "Apariencia",
    "section.category_order": "Orden de categorías",
    "section.on_finish": "Al finalizar",

    # ----- Buttons -----
    "btn.add_folder": "Agregar carpeta",
    "btn.add_many": "Agregar varias…",
    "btn.add_selected": "Agregar seleccionadas",
    "btn.select_all": "Marcar todas",
    "btn.deselect_all": "Desmarcar todas",
    "btn.clear": "Limpiar",
    "btn.choose": "Elegir",
    "btn.start_copy": "Iniciar copia",
    "btn.pause": "Pausar",
    "btn.resume": "Reanudar",
    "btn.skip_file": "Saltar archivo",
    "btn.cancel": "Cancelar",
    "btn.mark_all": "Marcar todo",
    "btn.unmark_all": "Desmarcar todo",
    "btn.expand_all": "Expandir todo",
    "btn.collapse_all": "Contraer todo",
    "btn.close": "Cerrar",
    "btn.start": "Iniciar",
    "btn.keep_copying": "Seguir copiando",
    "btn.choose_here": "Elegir aquí",
    "btn.choose_local": "Carpeta local",
    "btn.choose_mtp": "Dispositivo MTP",

    # ----- Field labels / hints -----
    "field.dest_hint": "Carpeta de destino",
    "field.overwrite": "Sobrescribir si ya existe",
    "field.dark_mode": "Modo oscuro",
    "field.language": "Idioma",
    "field.notify_on_finish": "Mostrar notificación al terminar",
    "field.shutdown_on_finish": "Apagar el equipo al terminar",

    # ----- Tooltips -----
    "tooltip.settings": "Configuración",
    "tooltip.move_left": "Mover a la izquierda",
    "tooltip.move_right": "Mover a la derecha",
    "tooltip.move_up": "Subir",
    "tooltip.move_down": "Bajar",
    "tooltip.remove_source": "Quitar esta carpeta",
    "tooltip.remove_game": "Quitar este juego de la cola",
    "tooltip.refresh": "Actualizar",

    # ----- File picker dialog titles -----
    "picker.add_source_title": "Agregar carpeta de origen",
    "picker.dest_title": "Carpeta de destino",
    "picker.add_many_parent_title": "Elegir carpeta padre",
    "picker.add_many_title": "Elegir carpetas a agregar",
    "picker.add_many_count": "{n} de {total} seleccionadas",
    "picker.mtp_title": "Elegir destino MTP",
    "picker.mtp_breadcrumb_root": "Dispositivos conectados",
    "picker.mtp_no_devices": "No se detectaron dispositivos MTP. Conecta el dispositivo y actualiza.",
    "picker.mtp_enum_error": "Error al enumerar dispositivos: {error}",
    "picker.mtp_empty_folder": "(carpeta vacía)",
    "picker.mtp_go_up": "Subir un nivel",

    # ----- Snackbars -----
    "snack.already_added": "Esa carpeta ya está agregada.",
    "snack.already_added_named": "«{name}» ya está en la lista.",
    "snack.no_subfolders": "La carpeta no tiene subcarpetas.",
    "snack.cant_list_parent": "No se puede leer la carpeta: {error}",
    "snack.added_many": "Se agregaron {n} carpetas.",
    "snack.added_many_partial": "Agregadas {n} de {total} (otras estaban vacías o ya cargadas).",
    "snack.scan_error": "Error al escanear: {error}",
    "snack.no_games_detected": "No se detectaron archivos .nsp/.nsz/.xci en esa carpeta.",
    "snack.added_singular": "Agregada: {name}  →  1 juego.",
    "snack.added_plural": "Agregada: {name}  →  {n} juegos.",
    "snack.specify_dest": "Especifica un destino primero.",
    "snack.cant_create_dest": "No se puede crear el destino: {error}",
    "snack.same_src_dst": "El origen y el destino son iguales.",
    "snack.no_files_selected": "No hay archivos seleccionados.",
    "snack.copy_done": "Copia completada sin errores.",
    "snack.copy_done_errors": "Copia finalizada con {errors} errores. Revisa los registros.",
    "snack.copy_done_zero": "Ningún archivo se copió. Revisa los registros.",
    "snack.copy_cancelled": "Copia cancelada.",

    # ----- Dialogs -----
    "dialog.confirm_copy_title": "Confirmar copia",
    "dialog.confirm_copy_body": "Se copiarán {n} archivos ({size}).\n¿Iniciar?",
    "dialog.cancel_copy_title": "Cancelar copia",
    "dialog.cancel_copy_body": "¿Cancelar la cola en progreso?",
    "dialog.settings_title": "Configuración",

    # ----- Status / queue area -----
    "status.ready": "Listo.",
    "status.no_games_yet": "Sin escanear todavía.",
    "status.copying_n": "Copiando {n} archivos · {size}",
    "status.cancelled_by_user": "Cancelado por el usuario.",
    "status.cancelled": "Cancelado.",
    "status.completed_size": "Completado · {size} copiados.",
    "status.completed_with_errors": "Completado con {errors} errores ({ok} OK · {skipped} omitidos).",
    "status.completed_zero": "Cola finalizada sin copiar nada (todos fallaron o se omitieron).",
    "status.skip_existing": "Omitido (ya existe): {name}",
    "status.skipped": "Omitido: {name}",
    "status.error_file": "Error: {name}",
    "status.current": "[{i}/{n}]  {cat} · {game} / {file}",

    # ----- Empty / placeholders -----
    "empty.no_sources": "Aún no se han agregado carpetas.",
    "empty.no_queue": "Agrega una carpeta arriba para ver la cola.",

    # ----- Help text -----
    "help.order": (
        "La de la izquierda se copia primero. "
        "Haz clic en una etiqueta para seleccionarla y luego usa ← → para moverla."
    ),
    "help.on_finish": (
        "Si activas «Apagar el equipo», al terminar verás un cuadro de "
        "confirmación con cuenta regresiva de 30 s. Si no lo cancelas, el "
        "equipo se apagará."
    ),

    # ----- Notifications + shutdown -----
    "notify.title": "Switch Queue Copy",
    "notify.done_ok": "Copia completada — {size} copiados.",
    "notify.done_with_errors": "Copia completada con {errors} errores ({ok} OK).",
    "notify.done_zero": "La cola finalizó sin copiar archivos.",
    "shutdown.dialog_title": "¿Apagar el equipo?",
    "shutdown.dialog_body": (
        "La cola finalizó sin errores. El equipo se apagará al terminar la "
        "cuenta regresiva. Si lo estás usando, cancela ahora."
    ),
    "shutdown.countdown": "Apagando en {seconds} segundos…",
    "shutdown.cancelled": "Apagado cancelado.",
    "shutdown.scheduled_with_countdown": "Apagado programado: cuenta regresiva de {seconds} s.",
    "shutdown.firing_now": "Ejecutando apagado del equipo…",
    "btn.cancel_shutdown": "Cancelar apagado",
    "btn.shutdown_now": "Apagar ahora",

    # ----- Generic -----
    "common.yes": "ON",
    "common.no": "OFF",
    "log.setting_changed": "Ajuste «{name}» → {value}.",

    # ----- Small labels -----
    "label.archivo": "Archivo",
    "label.cola": "Cola",
    "label.juego": "juego",
    "label.juegos": "juegos",

    # ----- Queue summary -----
    "summary.queue": "{sel_count} / {total_count} archivos · {sel_size} / {total_size}",

    # ----- Logs panel -----
    "logs.title": "Registros",
    "logs.empty": "(sin eventos todavía)",
    "logs.clear": "Limpiar registros",
    "logs.copy": "Copiar al portapapeles",
    "logs.close": "Ocultar registros",
    "logs.toggle": "Mostrar registros",
    "logs.copied": "Registros copiados al portapapeles.",
    "logs.copied_failed": "No se pudo copiar al portapapeles.",
    "tooltip.toggle_logs": "Mostrar / ocultar registros",

    # ----- Log lines (preformatted) -----
    "log.app_started": "Aplicación iniciada.",
    "log.theme_changed": "Tema cambiado a {mode}.",
    "log.locale_changed": "Idioma cambiado a {locale}.",
    "log.source_added": "Origen agregado: {name} ({n} juegos).",
    "log.source_removed": "Origen quitado: {name}.",
    "log.sources_cleared": "Todos los orígenes quitados.",
    "log.game_removed": "Juego quitado de la cola: {name}.",
    "log.dest_local": "Destino local: {path}.",
    "log.dest_mtp": "Destino MTP: {uri}.",
    "log.queue_started": "Cola iniciada: {n} archivos · {size}.",
    "log.queue_completed": "Cola completada: {ok} OK, {errors} errores, {skipped} omitidos ({size}).",
    "log.queue_cancelled": "Cola cancelada por el usuario.",
    "log.item_ok": "OK · {name}",
    "log.item_skip_existing": "Omitido (ya existe) · {name}",
    "log.item_skip_manual": "Omitido por el usuario · {name}",
    "log.item_error": "Error · {name}",
    "log.copy_paused": "Copia en pausa.",
    "log.copy_resumed": "Copia reanudada.",
    "log.mtp_unavailable": "Dispositivo MTP no disponible: {error}",
    "log.mtp_connected": "Dispositivo MTP encontrado: {name}",

    # ----- MTP errors -----
    "snack.mtp_unavailable": "Dispositivo MTP no detectado. Revisa la conexión.",
}
