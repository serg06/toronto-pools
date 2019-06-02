// globals that are filled in on page load
let selectDate;

const EMPTY_TIME = "\xa0"; // what we expect inside empty time <td>s


function onSelectDate(event) {
    // get the date they chose
    let date = event.target.value;
    let datecls = `date-${date}`;

    // hide old date
    for (let el of document.querySelectorAll('.pool-date.selected-date')) {
        el.style.display = 'none';
        el.classList.remove('selected-date')
    }

    for (let el of document.querySelectorAll('.pool-time.selected-date')) {
        el.style.display = 'none';
        el.classList.remove('selected-date')
    }

    // show all pools again
    for (let el of document.querySelectorAll('tr.pool-row')) {
        el.style.display = 'table-row';
    }

    // show new date
    for (let el of document.querySelectorAll(`.${datecls}.pool-date`)) {
        el.classList.add('selected-date')
        el.style.display = 'block';
    }

    for (let el of document.querySelectorAll(`.${datecls}.pool-time`)) {
        el.classList.add('selected-date')
        el.style.display = 'block';
    }

    // hide pointless rows
    for (let row of document.querySelectorAll('tr.pool-row')) {
        let time = row.querySelector('.selected-date').textContent;
        if (time === EMPTY_TIME) {
            row.style.display = 'none';
        }
    }
}

window.addEventListener('load', (event) => {
    console.log('page is fully loaded');

    selectDate = document.querySelector('#date-select');
    selectDate.addEventListener('change', onSelectDate);

});
