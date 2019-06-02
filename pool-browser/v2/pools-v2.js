// globals that are filled in on page load
let elSelectDate;

function getDate() {
    let today = new Date();
    let dd = today.getDate();

    let mm = today.getMonth() + 1;
    let yyyy = today.getFullYear();

    if (dd < 10) {
        dd = '0' + dd;
    }

    if (mm < 10) {
        mm = '0' + mm;
    }

    return `${yyyy}-${mm}-${dd}`;
}

function selectDate(date) {
    let el = elSelectDate.querySelector(`option[value='${date}']`);
    if (el === null) {
        console.log(`Error: Cannot find date '${date}'.`);
        return;
    }

    if (elSelectDate.value !== date) {
        console.log(`Manually change select date value to ${date}.`);
        elSelectDate.value = date;
    }

    // Ight here we go

    let datecls = `date-${date}`;

    // hide old times
    for (let el of document.querySelectorAll('.pool-time')) {
        el.style.display = 'none';
        el.classList.remove('selected-date')
    }

    // hide old pools
    for (let el of document.querySelectorAll('.pool-card')) {
        el.style.display = 'none';
        el.classList.remove('selected-date')
    }

    // show only chosen dates/pools
    for (let el of document.querySelectorAll(`.pool-time.${datecls}`)) {
        el.style.display = 'block';
        let cls_pool_name = el.getAttribute('pool-name');
        let pool_card = document.querySelector(`.pool-card.${cls_pool_name}`);
        pool_card.style.display = 'block';
    }
}

function onSelectDate(event) {
    // get the date they chose
    let date = event.target.value;

    // change to it
    selectDate(date);
}

window.addEventListener('load', (event) => {
    console.log('page is fully loaded');

    elSelectDate = document.querySelector('#date-select');
    elSelectDate.addEventListener('change', onSelectDate);

    selectDate(getDate());
});
