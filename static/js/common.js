function parseDate(dateString, lang = "esp") {
    if (lang !== "esp"){
        console.warn(`${lang} not implemented`);
    }
    let parts = dateString.split(' ');
    let day = parseInt(parts[0], 10);
    const monthNames = [
        'enero', 'febrero',
        'marzo', 'abril',
        'mayo', 'junio',
        'julio', 'agosto',
        'septiembre', 'octubre',
        'noviembre', 'diciembre'
    ];
    let month = monthNames.indexOf(parts[2].toLowerCase());
    let year = parseInt(parts[4], 10);
    let timeParts = parts[7].split(':');
    let hours = parseInt(timeParts[0], 10);
    let minutes = parseInt(timeParts[1], 10);
    let date = new Date(year, month, day, hours, minutes);
    return date.toISOString();
}

function dateFormat(date){
    const options = { day: 'numeric', month: 'long', year: 'numeric', hour: 'numeric', minute: 'numeric' };
    const locale = 'es-ES';

    const formattedDate = new Intl.DateTimeFormat(locale, options).format(date);
    const [justDate, time] = formattedDate.split(", ");

    return `${justDate} a las ${time}`;
}

const languageTable = {
    spanish: {
        search: "Buscar:",
        lengthMenu: "Mostrando _MENU_ registros",
        info: "Mostrando _START_ hasta _END_ de _TOTAL_ registros",
        emptyTable: "No hay información",
        zeroRecords: "No hay información",
        infoEmpty: "No se encontraron registros",
        infoFiltered: "(filtrados de un total de _MAX_ registros)",
        paginate: {
            first: "Primero",
            last: "Último",
            next: "Siguiente",
            previous: "Anterior",
        }
    }
};

function updateProgress(taskId, progressUrl, urlLog, postprocessingModal, csrfToken, logFileDefault){
    const progressDiv = postprocessingModal.getElementById("processProgress");
    let failure = false;
    $.ajax({
        url: progressUrl,
        type: 'GET',
        headers: {'X-CSRFToken': csrfToken},
        success: function(response){
            if (response.state === "PROGRESS"){
                let percentage = Number(response.details.step * 100 / response.details.total).toFixed(2);
                progressDiv.innerHTML = `<div class="progress-bar progress-bar-striped progress-bar-animated" style="width: ${percentage}%">${response.details.step}</div>`;
                const logDiv = postprocessingModal.getElementById("consoleLog");
                logDiv.children[0].innerHTML = response.details.logs;
                logDiv.scrollTop = logDiv.scrollHeight;
                setTimeout(updateProgress, 500, taskId);
            } else if (response.state === "STARTED") {
                progressDiv.innerHTML = `<div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 0">0</div>`;
                const logDiv = postprocessingModal.getElementById("consoleLog");
                logDiv.children[0].innerHTML = "Procesando...";
                logDiv.scrollTop = logDiv.scrollHeight;
                setTimeout(updateProgress, 500, taskId);
            } else if (response.state === "SUCCESS") {
                progressDiv.innerHTML = '<div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 100%">100%</div>';
                progressDiv.style.display = "none";
                progressDiv.innerHTML = '<div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 0%">0%</div>';
                postprocessingModal.getElementById('continuePostprocessing').disabled = false;
                postprocessingModal.getElementById('continuePostprocessing').style.display = "none";
                let logFileUrl;
                $.ajax({
                    url: urlLog,
                    type: 'GET',
                    headers: {'X-CSRFRToken': csrfToken},
                    success: function(response){
                        logFileUrl = response;
                    },
                    error: function(error){
                        console.error(error);
                        logFileUrl = logFileDefault;
                    }
                }).always(function() {
                    postprocessingModal.getElementById('postBody').innerHTML = `
                    <div class="alert alert-success">
                        <h6>Proceso completado con éxito</h6>
                    </div>
                    <div role="tab" id="showLog">
                        <h6>
                            <a role="button" data-bs-toggle="collapse" data-bs-target="#consoleLog" aria-expanded="true" aria-controls="consoleLog" class="">
                                Mostrar logs
                            </a>
                        </h6>
                    </div>
                    <div id="consoleLog" class="collapse" role="tabpanel" aria-labelledby="showLog">
                        <pre><code id="loggingContent"></code></pre>
                    </div>
                    <a class="btn btn-secondary" href="${logFileUrl}" download="${getFormattedDateTime()}.log">
                        <i class="fas fa-fw fa-download"></i>
                        <span>Descargar logs</span>
                    </a>
                    `;
                    const logDiv = postprocessingModal.getElementById("consoleLog");
                    logDiv.children[0].innerHTML = response.details.logs;
                    logDiv.scrollTop = logDiv.scrollHeight;
                });
            } else if (response.state === "FAILURE") {
                failure = true;
            } else {
                setTimeout(updateProgress, 500, taskId);
            }
        },
        error: function(error){
            console.warn(error);
            failure = true;
        },
    }).always(function() {
        if (failure) {
            progressDiv.style.display = "none";
            progressDiv.innerHTML = '<div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 0%">0%</div>';
            postprocessingModal.getElementById('continuePostprocessing').disabled = false;
            postprocessingModal.getElementById('continuePostprocessing').style.display = "none";
            let logDiv = postprocessingModal.getElementById("consoleLog");
            const content = logDiv.children[0].innerHTML;
            postprocessingModal.getElementById('postBody').innerHTML = `
            <div class="alert alert-danger">
                <h6>Ocurrió un error inesperado, favor contactar al administrador antes de cerrar esta ventana</h6>
            </div>
            <div role="tab" id="showLog">
                <h6>
                    <a role="button" data-bs-toggle="collapse" data-bs-target="#consoleLog" aria-expanded="true" aria-controls="consoleLog" class="">
                        Mostrar logs
                    </a>
                </h6>
            </div>
            <div id="consoleLog" class="collapse" role="tabpanel" aria-labelledby="showLog">
                <pre><code id="loggingContent"></code></pre>
            </div>
            `;
            logDiv = postprocessingModal.getElementById("consoleLog");
            logDiv.children[0].innerHTML = content;
            logDiv.scrollTop = logDiv.scrollHeight;
        }
    });
}