// globals that are filled in on page load
let selectDate;

function onSelectDate(event) {
    // get the date they chose
    let date = event.target.value;
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

window.addEventListener('load', (event) => {
    console.log('page is fully loaded');

    selectDate = document.querySelector('#date-select');
    selectDate.addEventListener('change', onSelectDate);
});
