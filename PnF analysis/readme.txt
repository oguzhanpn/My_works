# Read me:

## 1. How you should run the programme: 

    1.1. Update the tickers.txt file with the list of tickers you would like to analyze. Be careful with the format, there should be only the ticker names with one space between them in the txt file.
    
    1.2. From command line run pnf_triggers.py
    
    1.3. The programme will ask you to enter the required parameters (check parameters). Specify them if you want, or you can use default values of a parameter by just leaving the corresponding box empty.

    1.4. After you press OK, the triggers will be displayed. 

    1.5. Type the name of ticker you would like to plot one by one.
    


## 2. What does the the programme do?
    2.1. It first creates a csv file in downloaded_data folder with historical data for each ticker in the tickers.txt file. You can use those csv files for pnf Charting (The previous work). 
    
    2.2. It displays the tickers with boolish and bearish triggers. 

    2.3. It allows you to draw plots of stocks with triggers.
    


## 3. Parameters and default values:

    3.1. start_date = "2021-01-01" 
    
    3.2. end_date = dt.date.today() (If you want to use another day the format should be like: "2022-04-25")
    
    3.3. reversal_amount = 3
    
    3.4. box_size = float (If you don't specify any numbers box size is calculated according to the following rule:
        if the last available price of the stock is in [0, 5], then box_size = 0.25
        if the last available price of the stock is in (5, 20], then box_size = 0.5
        if the last available price of the stock is in (20, 100], then box_size = 1
        if the last available price of the stock is in (100, 200], then box_size = 2
        if the last available price of the stock is in (200, inf], then box_size = 4
     
    3.5. last_n_days = integer (If you don't specify any number, it will take all days from start_date to end_date)

    3.6. spread_trigger_wide = integer (This is the value for maximum number of columns that spread triple top breakout and spread triple bottom breakdown can occur.)
        
        