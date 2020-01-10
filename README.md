# Basic browsing of Toronto's leisure pool hours.

3 ways to use it:

## 1. Browse the pre-scraped data on my WIP interface

Located here: https://serg06.github.io/toronto-pools/. To see when I last scraped it, just check when I last committed
index.html.

## 2. Re-scrape and regenerate the web page yourself to make sure it's up-to-date

This is a static website (yay free Github hosting!) so for the sake of speed, all data is pre-scraped. To re-scrape:

- Clone the repo
- (Optional) delete pools.pkl to re-scrape the pool info
- Run `python3 generate_page.py`
- Open index.html with a browser

## 3. Get your hands dirty in the code

I've gone through the trouble of setting up scraping and parsing of the
[Toronto pools page](https://www.toronto.ca/data/parks/prd/swimming/dropin/leisure/index.html).
To start coding, all you have to do is:
- Open pools.py
- (Optional) delete pools.pkl to re-scrape the pool info
- Edit the date in the main function to the one you want info on (e.g. `find_pools_on("June 1", pool_info)`)
- Edit find_pools_on to manipulate the data any way you want. Currently it just sorts by how long the pool is open,
and then by start time.
