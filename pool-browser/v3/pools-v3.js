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
    // create pool cards
    let cards = [];
    for (let pool of Object.values(pool_info)) {
        let times = pool.availabilities[date];
        if (times === undefined) {
            continue;
        }

        cards.push(createPoolCard(pool, date));
    }

    // delete old cards
    let cards_container = document.querySelector('.pool-card-holder');
    while (cards_container.firstChild) {
        cards_container.removeChild(cards_container.firstChild);
    }

    // insert new ones
    for (let card of cards) {
        cards_container.appendChild(card);
    }
}

function timestampToText(timestamp) {
    // convert single start/end timestamp from pool_info into text
    // ex: 330 -> 5:30
    // ex: 300 -> 5

    if (timestamp < 0 || timestamp >= 1440) {
        console.log(`What is this timestamp you're giving me? ${timestamp}??`);
    }

    let hrs = parseInt(timestamp / 60);
    let mins = timestamp - hrs * 60;

    return `${hrs}:${mins.toString().padStart(2, '0')}`;
}

function timeToText(time) {
    // format time from pool_info as text
    // ex: 300, 330 -> 5 - 5:30am
    // basically: always add am/pm onto second timestamp, and only add it to first if first is AM and 2nd is PM.
    let start_str = timestampToText(time.start);
    let end_str = timestampToText(time.end);

    if ((time.end / 60) >= 12) {
        end_str += 'pm';
        if ((time.start / 60) < 12) {
            start_str += 'am';
        }
    } else {
        end_str += 'am';
    }

    return `${start_str} - ${end_str}`
}


// cache created pool cards; maybe this'll speed it up, who knows
let poolCardCache = {};


function createPoolCard(pool, date) {
    /*
    Sample pool:
        {"name": "York Recreation Centre", "classified_name": "york-recreation-centre", "availabilities": {"2019-07-09": [{"start": 870, "end": 930}], "2019-06-21": [{"start": 1170, "end": 1290}], "2019-06-08": [{"start": 810, "end": 945}], "2019-07-04": [{"start": 810, "end": 930}], "2019-07-06": [{"start": 810, "end": 945}], "2019-06-09": [{"start": 810, "end": 945}], "2019-07-07": [{"start": 810, "end": 945}], "2019-07-14": [{"start": 810, "end": 945}], "2019-07-17": [{"start": 810, "end": 930}], "2019-07-21": [{"start": 810, "end": 945}], "2019-06-16": [{"start": 810, "end": 945}], "2019-06-28": [{"start": 1170, "end": 1290}], "2019-06-13": [{"start": 1170, "end": 1245}], "2019-07-02": [{"start": 870, "end": 930}], "2019-06-20": [{"start": 1170, "end": 1245}], "2019-07-03": [{"start": 810, "end": 930}], "2019-06-06": [{"start": 1170, "end": 1245}], "2019-06-15": [{"start": 810, "end": 945}], "2019-07-27": [{"start": 810, "end": 945}], "2019-07-22": [{"start": 810, "end": 930}], "2019-06-30": [{"start": 810, "end": 945}], "2019-07-11": [{"start": 810, "end": 930}], "2019-06-29": [{"start": 810, "end": 945}], "2019-06-04": [{"start": 1170, "end": 1245}], "2019-06-11": [{"start": 1170, "end": 1245}], "2019-06-18": [{"start": 1170, "end": 1245}], "2019-07-13": [{"start": 810, "end": 945}], "2019-07-15": [{"start": 810, "end": 930}], "2019-06-14": [{"start": 1170, "end": 1290}], "2019-07-19": [{"start": 900, "end": 1020}, {"start": 1170, "end": 1290}], "2019-06-07": [{"start": 1170, "end": 1290}], "2019-06-25": [{"start": 1170, "end": 1245}], "2019-07-16": [{"start": 870, "end": 930}], "2019-07-05": [{"start": 900, "end": 1020}, {"start": 1170, "end": 1290}], "2019-06-02": [{"start": 810, "end": 945}], "2019-07-20": [{"start": 810, "end": 945}], "2019-07-18": [{"start": 810, "end": 930}], "2019-07-10": [{"start": 810, "end": 930}], "2019-07-25": [{"start": 810, "end": 930}], "2019-06-22": [{"start": 810, "end": 945}], "2019-06-27": [{"start": 1170, "end": 1245}], "2019-07-23": [{"start": 870, "end": 930}], "2019-07-08": [{"start": 810, "end": 930}], "2019-07-24": [{"start": 810, "end": 930}], "2019-07-26": [{"start": 900, "end": 1020}, {"start": 1170, "end": 1290}], "2019-07-12": [{"start": 900, "end": 1020}, {"start": 1170, "end": 1290}], "2019-06-23": [{"start": 810, "end": 945}]}, "address": "115 BLACK CREEK DR", "type": "indoor pool", "phone": "416 392-9675"}

    Sample output:
        <div class="pool-card Albert-Campbell-Collegiate-Institute">
            <div class="pool-name">Albert Campbell Collegiate Institute</div>
            <div class="pool-time date-2019-05-26">1 - 2pm</div>
            <div class="pool-time date-2019-05-27">5 - 6pm</div>
            <div class="pool-time date-2019-06-01">2 - 5pm</div>
        </div>
    """
    */

    let cached = poolCardCache[pool.name + date];
    if (cached !== undefined) {
        return cached;
    }

    let times = pool.availabilities[date];

    let card_el = document.createElement('div');
    card_el.classList.add('pool-card');

    let name_el = document.createElement('name');
    name_el.classList.add('pool-name');
    name_el.textContent = pool.name;
    card_el.appendChild(name_el);

    for (let time of times) {
        let time_el = document.createElement('div');
        time_el.classList.add('pool-time');
        time_el.textContent = timeToText(time);
        card_el.appendChild(time_el);
    }

    // expando this mf
    card_el.pool_info = pool;

    poolCardCache[pool.name + date] = card_el;

    return card_el;
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

    let today = getDate();
    elSelectDate.value = today;
    selectDate(today);
});
