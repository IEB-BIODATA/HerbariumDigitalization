function dateFormat(date, locale = "es-CL"){
    const options = { day: 'numeric', month: 'long', year: 'numeric', hour: 'numeric', minute: 'numeric' };
    if (locale.includes("es"))
        return (new Intl.DateTimeFormat(locale, options).format(date)).replace(", ", " a las ");
    else
        return new Intl.DateTimeFormat(locale, options).format(date);
}

function getTableLanguage(languageCode) {
    switch (languageCode) {
        case "es":
            return languageTable.spanish;
        case "en":
            return  languageTable.english;
        default:
            return languageTable.spanish;
    }
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
        decimal: ",",
        thousand: ".",
        paginate: {
            first: "Primero",
            last: "Último",
            next: "Siguiente",
            previous: "Anterior",
        }
    },
    english: {
        search: "Search:",
        lengthMenu: "Showing _MENU_ entries",
        info: "Showing _START_ to _END_ of _TOTAL_ entries",
        emptyTable: "No data available in table",
        zeroRecords: "No matching records found",
        infoEmpty: "Showing 0 to 0 of 0 entries",
        infoFiltered: "(filtered from _MAX_ total entries)",
        decimal: ".",
        thousand: ",",
        paginate: {
            first: "First",
            last: "Last",
            next: "Next",
            previous: "Previous",
        }
    }
};

function getFormattedDateTime() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    return `${year}_${month}_${day}-${hours}_${minutes}_${seconds}`;
}

function getStateClass(voucherState){
    switch(voucherState) {
        case 0:
            return 'bg-light text-dark';
        case 1:
            return 'bg-success text-white';
        case 2:
            return 'bg-danger text-white';
        case 3:
            return 'bg-warning text-dark';
        case 4:
            return 'bg-warning text-white';
        case 5:
            return 'bg-info text-dark';
        case 6:
            return 'bg-secondary text-white';
        case 7:
            return 'bg-primary text-white';
        case 8:
            return 'bg-light text-dark';
        default:
            return 'bg-info text-dark';
    }
}

function updateProgress(
    {
        taskId, progressUrl, urlLog,
        progressDOM, csrfToken, logFileDefault,
        started = false,
        onErrorMessage = (error) => {console.error(error)},
        successCallback = (success) => {console.log(success)},
        errorCallback = (error) => {console.error(error)},
    }){
    if (!started) {
        progressDOM.innerHTML = `
        <div class="progress" role="progressbar" aria-label="progress" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100" style="display: none;">
            <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 0">0%</div>
        </div>
        <div role="tab" class="show-log" id="show-log">
            <h6>
                <a role="button" data-bs-toggle="collapse" data-bs-target="#console-log" aria-expanded="true" aria-controls="console-log" class="">
                    <i class="fa-solid fa-caret-right"></i> Mostrar logs
                </a>
            </h6>
        </div>
        <div id="console-log" class="console-log collapse" role="tabpanel" aria-labelledby="show-log">
            <pre><code id="logging-content"></code></pre>
        </div>
        `;
        progressDOM.getElementsByClassName("console-log")[0].addEventListener('show.bs.collapse', event => {
            event.explicitOriginalTarget.innerHTML = '<i class="fa-solid fa-caret-down"></i> Ocultar logs';
        });
        progressDOM.getElementsByClassName("console-log")[0].addEventListener('hide.bs.collapse', event => {
            event.explicitOriginalTarget.innerHTML = '<i class="fa-solid fa-caret-right"></i> Mostrar logs';
        });
    }
    started = true;
    const progressDiv = progressDOM.getElementsByClassName("progress")[0]
    const logDiv = progressDOM.getElementsByClassName("console-log")[0];
    let failure = false;
    let ended = false;
    let errorData = {};
    $.ajax({
        url: progressUrl,
        type: 'GET',
        headers: {'X-CSRFToken': csrfToken},
        success: function(response){
            if (response.state === "PROGRESS"){
                progressDiv.style.display = "";
                progressDiv
                    .getElementsByClassName("progress-bar")[0]
                    .style
                    .width = `${Number(response.details.step * 100 / response.details.total).toFixed(2)}%`;
                progressDiv
                    .getElementsByClassName("progress-bar")[0]
                    .innerText = response.details.step;
                logDiv.children[0].innerHTML = response.details.logs;
                logDiv.scrollTop = logDiv.scrollHeight;
                setTimeout(updateProgress, 500, {
                    taskId: taskId,
                    progressUrl: progressUrl,
                    urlLog: urlLog,
                    progressDOM: progressDOM,
                    csrfToken: csrfToken,
                    logFileDefault: logFileDefault,
                    started: started,
                    onErrorMessage: onErrorMessage,
                    successCallback: successCallback,
                    errorCallback: errorCallback
                });
            } else if (response.state === "STARTED") {
                progressDiv.style.display = "";
                progressDiv
                    .getElementsByClassName("progress-bar")[0]
                    .style
                    .width = 0;
                progressDiv
                    .getElementsByClassName("progress-bar")[0]
                    .innerText = 0;
                logDiv.children[0].innerHTML = "Process started...";
                logDiv.scrollTop = logDiv.scrollHeight;
                setTimeout(updateProgress, 500, {
                    taskId: taskId,
                    progressUrl: progressUrl,
                    urlLog: urlLog,
                    progressDOM: progressDOM,
                    csrfToken: csrfToken,
                    logFileDefault: logFileDefault,
                    started: started,
                    onErrorMessage: onErrorMessage,
                    successCallback: successCallback,
                    errorCallback: errorCallback
                });
            } else if (response.state === "PENDING") {
                progressDiv.style.display = "";
                progressDiv
                    .getElementsByClassName("progress-bar")[0]
                    .style
                    .width = 0;
                progressDiv
                    .getElementsByClassName("progress-bar")[0]
                    .innerText = 0;
                logDiv.children[0].innerHTML = "Sending task, pending response...";
                logDiv.scrollTop = logDiv.scrollHeight;
                setTimeout(updateProgress, 500, {
                    taskId: taskId,
                    progressUrl: progressUrl,
                    urlLog: urlLog,
                    progressDOM: progressDOM,
                    csrfToken: csrfToken,
                    logFileDefault: logFileDefault,
                    started: started,
                    onErrorMessage: onErrorMessage,
                    successCallback: successCallback,
                    errorCallback: errorCallback
                });
            } else if (response.state === "SUCCESS") {
                progressDiv.style.display = "";
                progressDiv
                    .getElementsByClassName("progress-bar")[0]
                    .style
                    .width = 100;
                progressDiv.style.display = "none";
                progressDiv
                    .getElementsByClassName("progress-bar")[0]
                    .style
                    .width = 0;
                logDiv.children[0].innerHTML = response.details.logs;
                logDiv.scrollTop = logDiv.scrollHeight;
                ended = true;
            } else if (response.state === "FAILURE") {
                failure = true;
                ended = true;
            } else if (response.state === "ERROR") {
                failure = true;
                logDiv.children[0].innerHTML = response.details.logs;
                logDiv.scrollTop = logDiv.scrollHeight;
                ended = true;
                errorData = response.details.error;
            } else {
                setTimeout(updateProgress, 500, {
                    taskId: taskId,
                    progressUrl: progressUrl,
                    urlLog: urlLog,
                    progressDOM: progressDOM,
                    csrfToken: csrfToken,
                    logFileDefault: logFileDefault,
                    started: started,
                    onErrorMessage: onErrorMessage,
                    successCallback: successCallback,
                    errorCallback: errorCallback
                });
            }
        },
        error: function(error){
            console.warn(error);
            failure = true;
            ended = true;
        },
    }).always(function() {
        if (ended) {
            let logFileUrl;
            $.ajax({
                url: urlLog,
                type: 'GET',
                headers: {'X-CSRFRToken': csrfToken},
                success: function (response) {
                    logFileUrl = response;
                },
                error: function (error) {
                    console.error(error);
                    logFileUrl = logFileDefault;
                }
            }).always(function () {
                progressDOM.insertAdjacentHTML('beforeend', `
                <a class="btn btn-secondary" href="${logFileUrl}" download="${getFormattedDateTime()}.log">
                    <i class="fas fa-fw fa-download"></i>
                    <span>Descargar logs</span>
                </a>
                `);
                if (failure) {
                    progressDiv.style.display = "none";
                    progressDiv
                        .getElementsByClassName("progress-bar")[0]
                        .style
                        .width = 0;
                    progressDiv
                        .getElementsByClassName("progress-bar")[0]
                        .innerText = 0;
                    $(progressDOM).prepend(`
                    <div class="alert alert-danger">
                        ${onErrorMessage(errorData)}
                    </div>
                    `);
                    $(progressDOM).show("slow", "swing");
                    logDiv.scrollTop = logDiv.scrollHeight;
                    errorCallback(errorData);
                } else {
                    $(progressDOM).prepend(`
                    <div class="alert alert-success">
                        <h6>Proceso completado con éxito</h6>
                    </div>
                    `);
                    $(progressDOM).show("slow", "swing");
                    successCallback();
                }
            });
        }
    });
}

function darkenColor(hex, darkness) {
    // Convert hex to RGB
    let r = parseInt(hex.substring(1, 3), 16);
    let g = parseInt(hex.substring(3, 5), 16);
    let b = parseInt(hex.substring(5, 7), 16);

    // Darken the color
    r = Math.max(0, r - darkness);
    g = Math.max(0, g - darkness);
    b = Math.max(0, b - darkness);

    // Convert RGB back to hex
    return '#' + ((r << 16) | (g << 8) | b).toString(16).padStart(6, '0');
}
