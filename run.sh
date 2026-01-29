#!/bin/bash
cd scripts/
# Create a directory to store today's analysis in data/
ANALYSIS_DIR="../data/$(date +"%m-%d-%Y")"
mkdir -p "$ANALYSIS_DIR"

# Get current time for file naming
TIMESTAMP=$(date +"%H-%M-%S")

# Update user about zacks new #1 additions
python zacks.py

# Run insider trading analysis pipeline
python scrape.py insider | python analyzer.py insider
# Check if insider analysis was successful
if [ $? -eq 0 ]; then
  # Move insider files to the analysis directory with timestamp
  mv insider_trading_data.csv "$ANALYSIS_DIR/insider_trading_data_${TIMESTAMP}.csv" 2>/dev/null
else
  echo "Error: insider analysis failed."
  exit 1
fi

# Run congress trading analysis pipeline
python scrape.py congress | python analyzer.py congress
# Check if congress analysis was successful
if [ $? -eq 0 ]; then
  # Move congress files to the analysis directory with timestamp
  mv congress_trading_data.csv "$ANALYSIS_DIR/congress_trading_data_${TIMESTAMP}.csv" 2>/dev/null
else
  echo "Error: Congress analysis failed."
  exit 1
fi

# Run congress purchases only analysis (silenced output, just create CSV)
python congress_df.py -P -r -o congress_purchases_only_${TIMESTAMP}.csv >/dev/null 2>&1
# Check if congress purchases analysis was successful
if [ $? -eq 0 ]; then
  # Move congress purchases file to the analysis directory
  mv congress_purchases_only_${TIMESTAMP}.csv "$ANALYSIS_DIR/" 2>/dev/null
else
  echo "Error: Congress purchases analysis failed."
  exit 1
fi

# Display a message about the output files
echo -e "\nGenerated files in $ANALYSIS_DIR:"
