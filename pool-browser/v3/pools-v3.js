const oneDayMinutes = 60 * 24;
const dataMatrixAPIURL = 'https://www.mapquestapi.com/directions/v2/routematrix'; // ?key=...
const maxMatrixAPISize = 100;
const requests = [];
const responses = [];
const apiKeyLocalStorageKey = "ApiKeyMapQuest";

const sortOptions = {
    name: (cardEl, cardEl2) => {
        if (cardEl.pool_info.name > cardEl2.pool_info.name) {
            return 1;
        } else if (cardEl.pool_info.name < cardEl2.pool_info.name) {
            return -1;
        } else {
            return 0;
        }
    },
    distance: (cardEl, cardEl2) => {
        let d1 = cardEl.pool_info.distance;
        let d2 = cardEl2.pool_info.distance;

        if (d1 === d2) {
            return 0;
        }

        // if d1 loses, d2 wins (is closer)
        if (d1 === undefined) {
            console.log(`WARN: Pool ${cardEl.pool_info.name} has no distance.`);
            return 1;
        }

        // and vice versa
        if (d2 === undefined) {
            console.log(`WARN: Pool ${cardEl2.pool_info.name} has no distance.`);
            return -1;
        }

        if (d1 < d2) {
            return -1;
        } else if (d1 > d2) {
            return 1;
        } else {
            // should never reach here
            return 0;
        }
    },
    time: (cardEl, cardEl2) => {
        let t1 = cardEl.pool_info.time;
        let t2 = cardEl2.pool_info.time;

        if (t1 === t2) {
            return 0;
        }

        // if d1 loses, d2 wins (is closer)
        if (t1 === undefined) {
            console.log(`WARN: Pool ${cardEl.pool_info.name} has no time.`);
            return 1;
        }

        // and vice versa
        if (t2 === undefined) {
            console.log(`WARN: Pool ${cardEl2.pool_info.name} has no time.`);
            return -1;
        }

        if (t1 < t2) {
            return -1;
        } else if (t1 > t2) {
            return 1;
        } else {
            // should never reach here
            return 0;
        }
    },
    length: (cardEl, cardEl2) => {
        let date = elSelectDate.value;

        let length1 = Math.max(...cardEl.pool_info.availabilities[date].map(avail => avail.end - avail.start));
        let length2 = Math.max(...cardEl2.pool_info.availabilities[date].map(avail => avail.end - avail.start));

        // reverse sort
        if (length1 > length2) {
            return -1;
        } else if (length1 < length2) {
            return 1;
        } else {
            return sortOptions.name(cardEl, cardEl2);
        }
    },
    soonest: (cardEl, cardEl2) => {
        // TODO: Get EST time? https://stackoverflow.com/a/36206597/5090928
        let date = elSelectDate.value;

        let d = new Date();
        let timeInMinutes = d.getHours() * 60 + d.getMinutes();

        let soonest1 = Math.min(...cardEl.pool_info.availabilities[date].map(avail =>
            (avail.start - timeInMinutes >= 0) ? avail.start - timeInMinutes : oneDayMinutes));
        let soonest2 = Math.min(...cardEl2.pool_info.availabilities[date].map(avail =>
            (avail.start - timeInMinutes >= 0) ? avail.start - timeInMinutes : oneDayMinutes));

        if (soonest1 > soonest2) {
            return 1;
        } else if (soonest1 < soonest2) {
            return -1;
        } else {
            return sortOptions.length(cardEl, cardEl2);
        }
    },
    start: (cardEl, cardEl2) => {
        let date = elSelectDate.value;

        let earliest1 = Math.min(...cardEl.pool_info.availabilities[date].map(avail => avail.start));
        let earliest2 = Math.min(...cardEl2.pool_info.availabilities[date].map(avail => avail.start));

        if (earliest1 > earliest2) {
            return 1;
        } else if (earliest1 < earliest2) {
            return -1;
        } else {
            return sortOptions.name(cardEl, cardEl2);
        }
    },
    end: (cardEl, cardEl2) => {
        let date = elSelectDate.value;

        let earliest1 = Math.min(...cardEl.pool_info.availabilities[date].map(avail => avail.end));
        let earliest2 = Math.min(...cardEl2.pool_info.availabilities[date].map(avail => avail.end));

        if (earliest1 > earliest2) {
            return 1;
        } else if (earliest1 < earliest2) {
            return -1;
        } else {
            return sortOptions.name(cardEl, cardEl2);
        }
    }
};

// globals that are filled in on page load
let elSelectDate, elSelectSort, elCardHolder, elInputAddress, elDownloadResult;

function removeChildren(el) {
    while (el.firstChild) {
        el.removeChild(el.firstChild);
    }
}

function sortCards(sortOption) {
    console.log(`sortCards(${sortOption})`);

    // get sorter
    let compareFn = sortOptions[sortOption];
    if (compareFn === undefined) {
        console.log(`ERR: No sort function called ${compareFn}`);
        return;
    }

    // get pool card elements
    let poolCardEls = document.querySelectorAll('.pool-card');
    let poolCardArr = Array.from(poolCardEls);

    // sort elements
    poolCardArr.sort(compareFn);

    // stick 'em back in!

    // for (let [i, el] of poolCardArr.entries()) {
    //     elCardHolder.replaceChild(el, poolCardEls[i]);
    // }

    removeChildren(elCardHolder);
    for (let card of poolCardArr) {
        elCardHolder.appendChild(card);
    }
}

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
    removeChildren(elCardHolder);

    // insert new ones
    for (let card of cards) {
        elCardHolder.appendChild(card);
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

    let times = pool.availabilities[date];

    let card_el = document.createElement('div');
    card_el.classList.add('pool-card');

    let name_el = document.createElement('name');
    name_el.classList.add('pool-name');
    name_el.textContent = pool.name;
    if (pool.distance) {
        name_el.textContent += ` (~${pool.distance.toFixed(1)}km)`;
    }
    if (pool.time) {
        name_el.textContent += ` (~${Math.ceil(pool.time / 60)}min)`;
    }
    card_el.appendChild(name_el);

    for (let time of times) {
        let time_el = document.createElement('div');
        time_el.classList.add('pool-time');
        time_el.textContent = timeToText(time);
        card_el.appendChild(time_el);
    }

    // expando this mf
    card_el.pool_info = pool;

    return card_el;
}

function appendDownloadStatus(status, err = false) {
    let el = document.createElement('li');
    el.textContent = status;
    if (err) {
        el.classList.add('err-msg');
    }
    elDownloadResult.appendChild(el);
    return el;
}

function updateDistances(address, pools) {
    // give them an update
    let elStatus = appendDownloadStatus('downloading batch of distances/times...');

    let apikey = document.querySelector('#input-apikey').value;
    // save API key so they don't have to re-enter it every visit
    localStorage.setItem(apiKeyLocalStorageKey, apikey);

    let req;
    if (window.XMLHttpRequest) { // Mozilla, Safari, IE7+ ...
        req = new XMLHttpRequest();
    } else if (window.ActiveXObject) { // IE 6 and older
        console.log('WARN: XMLHttpRequest not supported, hopefully should still work.');
        req = new ActiveXObject("Microsoft.XMLHTTP");
    } else {
        console.log('ERR: Ajax requests not supported on this browser.');
        elDownloadResult.removeChild(elStatus);
        appendDownloadStatus('ERR: NO AJAX', true);
        return;
    }

    let URL = `${dataMatrixAPIURL}?key=${apikey}`;

    // extract addresses in reliable order: Get pools, sort by name, then extract addresses.
    pools.sort((pool1, pool2) => pool1.name > pool2.name ? 1 : pool1.name < pool2.name ? -1 : 0);
    let addresses = pools.map(pool => `${pool.address}, Toronto ON`);

    // add own address as first entry; the one to get distances too
    addresses.unshift(address);

    let body = {"locations": addresses};
    requests.push(body);

    req.onreadystatechange = function () {
        if (req.readyState !== XMLHttpRequest.DONE) {
            // If not ready yet, ignore.
            return;
        }

        if (req.status !== 200) {
            console.log(`ERR: MapQuest responded with non-200 status: ${req.status}`);
            elDownloadResult.removeChild(elStatus);
            appendDownloadStatus('ERR: unexpected (non-200) response from MapQuest', true);
            return;
        }

        // console.log(`Success! Response: ${JSON.stringify(this.response)}`);
        elDownloadResult.removeChild(elStatus);
        onDistanceResponse(this.response, pools);
    };

    req.open('POST', URL);
    req.send(JSON.stringify(body));
    // response = JSON.parse(response);
}

function onDistanceResponse(response, requestedPools) {
    response = JSON.parse(response);
    responses.push(response);

    // check for errors
    if (response.route) {
        appendDownloadStatus(`ERR: The location finder doesn\'t seem to like your location. It says "${response.info.messages[0]}".`, true);
        return;
    }

    // extract distances (and times) from response
    let distances = response.distance;
    let times = response.time;

    // assert as expected
    let dl = distances.length;
    let ll = response.locations.length;
    let tl = times.length;
    if (((dl !== ll) && (dl !== ll - 1)) || ((tl !== ll) && (tl !== ll - 1))) {
        console.log(`ERROR: dl: ${dl}, tl: ${tl}, ll: ${ll}`);
        appendDownloadStatus('ERR: unexpected response (number of distances/times doesn\'t match number of pools...)', true);
        return;
    }

    // sometimes a little weird...
    if (distances.length === response.locations.length) {
        if (distances[0] !== 0) {
            console.log(`ERR: distances[0] != ${distances[0]}`);
            appendDownloadStatus('ERR: unexpected distances returned (distance to self is non-zero)', true);
            return;
        }
        distances.shift();
    }
    if (times.length === response.locations.length) {
        if (times[0] !== 0) {
            console.log(`ERR: times[0] != ${times[0]}`);
            appendDownloadStatus('ERR: unexpected times returned (time to self is non-zero)', true);
            return;
        }
        times.shift();
    }

    // append to pool info
    for (let i = 0; i < distances.length; i++) {
        requestedPools[i].distance = distances[i];
        requestedPools[i].time = times[i];
    }

    if (Math.max(...distances) > 50) {
        appendDownloadStatus('ERR: one of the distances is >50km... maybe just a MapQuest bug, try re-downloading', true);
    }
    if (Math.min(...distances) === 0) {
        appendDownloadStatus('ERR: one of the distances is 0km... maybe just a MapQuest bug, try re-downloading', true);
    }

    // refresh cards (hacky)
    selectDate(elSelectDate.value);
}

function onSelectDate(event) {
    // get the date they chose
    let date = event.target.value;

    // change to it
    selectDate(date);
    sortCards(elSelectSort.value);
}

function onSelectSort(event) {
    // get the sort option they chose
    let sortOption = event.target.value;

    // change to it
    sortCards(sortOption);
}

function onPressDownloadAddresses(event) {
    // reset download status
    removeChildren(elDownloadResult);

    let address = elInputAddress.value;
    if (address.trim().length === 0) {
        console.log('Really?');
        return;
    }

    // can only do max 100 here, so let's split it up
    let all_pools = Object.values(pool_info);
    // subtract 1 from api size, 'cause always need to append our own address first
    for (let i = 0; i < (all_pools.length / (maxMatrixAPISize - 1)); i++) {
        console.log(`Update addresses for pools ${i * (maxMatrixAPISize - 1)}...${(i + 1) * (maxMatrixAPISize - 1) - 1}`);
        let pools = all_pools.slice(i * (maxMatrixAPISize - 1), (i + 1) * (maxMatrixAPISize - 1));
        updateDistances(address, pools);
    }
}

function addDownloadStatus(status) {
    // create element
    // return it, so we can delete it later
}

window.addEventListener('load', (event) => {
    // get elements
    elSelectDate = document.querySelector('#date-select');
    elSelectSort = document.querySelector('#sort-select');
    elCardHolder = document.querySelector('.pool-card-holder');
    elInputAddress = document.querySelector('#input-address');
    elDownloadResult = document.querySelector('#download-result');

    // hook up date select
    elSelectDate.addEventListener('change', onSelectDate);
    let today = getDate();
    elSelectDate.value = today;
    selectDate(today);

    // hook up sort select
    elSelectSort.addEventListener('change', onSelectSort);

    // hook up distance checker
    document.querySelector('#btn-distance-update').addEventListener('click', onPressDownloadAddresses);

    // stick in previous API key, if exists
    document.querySelector('#input-apikey').value = localStorage.getItem(apiKeyLocalStorageKey) || '';
});
