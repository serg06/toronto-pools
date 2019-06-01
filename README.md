Super basic browsing of Toronto's leisure pool hours.

What it does:
- Downloads latest pool info from https://www.toronto.ca/data/parks/prd/swimming/dropin/leisure/index.html
- Parses page and reverts pool info into usable objects
- Has a function that browses through these objects for you and prints all pools available on a given day

How to work it:
- Open pools.py
- Edit the date in the main function to the one you want info on (e.g. find_pools_on("June 1", pool_info))
- Run it with python3
