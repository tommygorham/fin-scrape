#!/bin/bash

# Define list of tickers
TICKERS=("NFLX" "TSM" "NVDA" "SNDK" "MU" "HUT" "PLTR" "BE" "NBIS" "CRWD" "IREN" )
#TICKERS=("NFLX" "TSM" "NVDA" "AMD" "GOOGL" "SNDK" "MU" "HUT" "PLTR" "BE" "NBIS" "CRWD" "NOW" )
#"CRSP" "BIDU" "SHOP" "BABA" "TXG" "TSLA" "COIN" "ROKU" "TEM" "HOOD" "OKLO" "NEE" "DUK" "SMR"


# Remove and recreate analysis directory
if [ -d ~/Code/stocks/analysis ]; then
    rm -rf ~/Code/stocks/analysis
fi
mkdir -p ~/Code/stocks/analysis

# Awk script to clean and format lines
read -r -d '' AWK_CLEAN << 'AWKSCRIPT'
BEGIN { FS=":" }
{
    path = $1
    content = $2
    for (i=3; i<=NF; i++) content = content ":" $i
    
    # Extract date from path (./MM-DD-YYYY/...) and convert to YYYY-MM-DD
    path_date = ""
    if (match(path, /[0-9][0-9]-[0-9][0-9]-[0-9][0-9][0-9][0-9]/)) {
        path_date_str = substr(path, RSTART, RLENGTH)
        split(path_date_str, pd, "-")
        path_date = pd[3] "-" pd[1] "-" pd[2]
    }
    
    # Check for transaction date at end (YYYY-MM-DD)
    if (match(content, /[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]$/)) {
        trans_date = substr(content, RSTART, RLENGTH)
        main = substr(content, 1, RSTART-2)
        n = split(main, f, ",")
        ticker = f[1]
        name_party = f[3]
        for (i=4; i<=n; i++) name_party = name_party "," f[i]
        gsub(/"/, "", name_party)
        gsub(/House/, " House", name_party)
        gsub(/Senate/, " Senate", name_party)
        gsub(/  +/, " ", name_party)
        gsub(/^ +| +$/, "", name_party)
        print trans_date ", " ticker ", " name_party
    } else {
        # Non-standard format - use path date
        print path_date ", " content
    }
}
AWKSCRIPT

# Search for each ticker in data directory
cd data
for ticker in "${TICKERS[@]}"; do
    grep -r "$ticker" . > ~/Code/stocks/analysis/${ticker}_IN.txt
done

cd ../analysis

# Process each ticker into clean format
for ticker in "${TICKERS[@]}"; do
    awk "$AWK_CLEAN" ${ticker}_IN.txt | sort -r -t',' -k1 | awk '!seen[$0]++' > ${ticker}.txt
done

# Merge all ticker files into ALL.txt (newest first, deduplicated)
cat "${TICKERS[@]/%/.txt}" | sort -r -t',' -k1 | awk '!seen[$0]++' > ALL.txt

# Clean up intermediate files
rm -f *_IN.txt

# Clean up individual ticker files
for ticker in "${TICKERS[@]}"; do
rm -f ${ticker}.txt
done
