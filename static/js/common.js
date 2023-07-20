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
