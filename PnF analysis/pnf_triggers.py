import pandas as pd
import numpy as np
import datetime as dt
import matplotlib.pyplot as plt
from matplotlib.ticker import (AutoMinorLocator)
import warnings
import seaborn as sns
import yfinance as yf
import sys
warnings.filterwarnings("ignore")
import easygui
import locale

class PnfAnalysis():
    def __init__(self, ticker, start_date="2021-01-01", end_date=dt.date.today(), reversal_amount=3, box_size=None, last_n_days=None, spread_trigger_wide=15, get_data=True):
        self.ticker = ticker
        self.start_date = start_date
        self.end_date = end_date
        self.reversal_amount = reversal_amount
        self.box_size = box_size
        self.last_n_days = last_n_days
        self.get_data = get_data

        data = self.import_data()
        self.data = data
        self.pnf_data = self.create_pnf_data(data=data)
        self.spread_trigger_wide = spread_trigger_wide

    def import_data(self):
        end_date_for_yf = dt.datetime.strptime(end_date, "%Y-%m-%d").date() + dt.timedelta(days=1)
        df = yf.download(self.ticker, start=self.start_date, end=end_date_for_yf)
        file_path = "downloaded_data/{}_from_{}_to_{}.csv".format(self.ticker, self.start_date, self.end_date).replace("-", "_")
        if (self.get_data):
            df.to_csv(file_path, sep=";")
        return df

    def create_pnf_data(self, data):

        if (self.box_size == None):
            # First, determine the box size according to the last closing price if it is not specified:
            last_price = data.Close[len(data) - 1]
            self.box_size = 0.05
            if (last_price > 1):
                self.box_size = 0.10
            if (last_price > 2):
                self.box_size = 0.25
            if (last_price > 5):
                self.box_size = 0.5
            if (last_price > 20):
                self.box_size = 1
            if (last_price > 100):
                self.box_size = 2
            if (last_price > 200):
                self.box_size = 4

            # Second: Initialize the first streak
        lowest_price = data.iloc[0, ].Low
        highest_price = data.iloc[0, ].High
        diff = highest_price - lowest_price
        i = 1
        while (diff < (self.reversal_amount + 1) * self.box_size) and (i < len(data)):
            lowest_price = min(lowest_price, data.iloc[i, ].Low)
            highest_price = max(highest_price, data.iloc[i, ].High)
            diff = highest_price - lowest_price
            i += 1

        pnf_data = pd.DataFrame(columns=["open", "close"])

        if ((highest_price - data.iloc[0, ].Low) > (data.iloc[0, ].High - lowest_price)):
            # If highest price is increased more than lowest price decreased --> first streak is "X". Otherwise "O"
            current_streak = "X"
            pnf_open = data.iloc[0, ].Low
            pnf_close = highest_price
            pnf_data.loc[0, "open"] = pnf_open
            pnf_data.loc[0, "close"] = pnf_close

        else:
            current_streak = "O"
            pnf_open = data.iloc[0, ].High
            pnf_close = lowest_price
            pnf_data.loc[0, "open"] = pnf_open
            pnf_data.loc[0, "close"] = pnf_close

            # Third: update the streaks for each day:
            # If current streak is "X":
            #    1. Update upper interval (= High_today if it exceeds High_yesterday)
            #    2. Check if the streak ends (it ends if todays min is below upper_interval - box_size)
            #    3. if ends --> start an "O" streak, skip the next row in pnf_data.  If not ends do nothing.
            #
            # Apply similar logic if current_streak is "O"
        closing_dates_list = []
        for j in range(1, len(data)):
            if (current_streak == "X"):
                pnf_close = max(pnf_close, data.iloc[j, ].High)  # 1. Update upper interval

                if (data.iloc[j, ].Low < pnf_close - (
                        self.reversal_amount + 1) * self.box_size):  # 2. Check if the streak ends
                    new_row = {"open": pnf_open, "close": pnf_close}
                    pnf_data = pnf_data.append(new_row, ignore_index=True)

                    closing_dates_list.append(data.index[j])
                    current_streak = "O"
                    pnf_open = pnf_close - self.box_size
                    pnf_close = data.iloc[j, ].Low

            else:
                pnf_close = min(pnf_close, data.iloc[j, ].Low)  # 1. Update Lower interval

                if (data.iloc[j, ].High > pnf_close + (
                        self.reversal_amount + 1) * self.box_size):  # 2. Check if the streak ends
                    new_row = {"open": pnf_open, "close": pnf_close}
                    pnf_data = pnf_data.append(new_row, ignore_index=True)
                    closing_dates_list.append(data.index[j])

                    current_streak = "X"
                    pnf_open = pnf_close + self.box_size
                    pnf_close = data.iloc[j, ].High

        new_row = {"open": pnf_open, "close": pnf_close}
        pnf_data = pnf_data.append(new_row, ignore_index=True)
        closing_dates_list.append(data.index[-1])

        pnf_data.index = pnf_data.index.set_names(["rownbr"])
        pnf_data = pnf_data.drop(0)
        pnf_data = pnf_data.astype(float)
        pnf_data = self.box_size * ((pnf_data / self.box_size).round())

        self.closing_dates_list = closing_dates_list

        return pnf_data

    def create_plot_from_pnf_data(self, figure_size=(18, 15), chart_name="Point and Figure Chart", grid_freq_y=1,
                                  grid_freq_x=1, lines = list()):
        # Create the plot:
        fig, ax = plt.subplots(figsize=figure_size)

        prev_marker = "X"
        for i in self.pnf_data.index:
            if (self.pnf_data.loc[i, "close"] > self.pnf_data.loc[i, "open"]):
                y_values = np.arange(self.pnf_data.loc[i, "open"], self.pnf_data.loc[i, "close"], self.box_size)
                tmp_marker = "X"
                prev_marker = "X"
                cl = "g"

            elif (self.pnf_data.loc[i, "close"] < self.pnf_data.loc[i, "open"]):
                y_values = np.arange(self.pnf_data.loc[i, "close"], self.pnf_data.loc[i, "open"], self.box_size)
                tmp_marker = "o"
                prev_marker = "o"
                cl = "r"

            elif (prev_marker == "X"):
                y_values = np.arange(self.pnf_data.loc[i, "close"], self.pnf_data.loc[i, "open"], self.box_size)
                tmp_marker = "o"
                cl = "r"

            else:
                y_values = np.arange(self.pnf_data.loc[i, "open"], self.pnf_data.loc[i, "close"], self.box_size)
                tmp_marker = "X"
                cl = "g"

            sns.scatterplot(x=i, y=y_values, marker=tmp_marker, s=100, color=cl, ax = ax)

        ax.set_ylabel("Price Level")
        ax.set_title(chart_name)
        ax.yaxis.set_minor_locator(AutoMinorLocator(grid_freq_y))
        ax.xaxis.set_minor_locator(AutoMinorLocator(grid_freq_x))

        ax.grid(visible=True, which='major', linestyle='--')
        ax.grid(visible=True, which='minor', linestyle=':')

        # Draw the lines:
        for i in lines:
            sns.lineplot( x=[i[0], i[1]], y=[i[2], i[3]], color = 'blue', ax = ax)

        fig.show()

    def check_triggers(self):
        # First add type column to pnf data:
        pnf_with_type = self.pnf_data.copy(deep=False)
        pnf_with_type["type"] = "X"
        pnf_with_type.loc[pnf_with_type.open > pnf_with_type.close, "type"] = "O"
        trigger_list = []
        # Format in trigger_list: (trigger_name, index (=column # in the graph), length (=horizontal length in graph))

        # for each row of pnf_data check the triggers:
        for i in pnf_with_type.index:

            # Check double top and double bottom triggers Also check ascending triples:
            if (i <= len(pnf_with_type) - 2):
                if (pnf_with_type.loc[i, "type"] == "X"):
                    if (check_double_top_breakout(pnf_with_type, i)):
                        trigger_list.append(
                            ("double_top_breakout", i, 2))  # If there is ascending triple top, remove this

                        # Now check if there is ascending triple top:
                        if (i + 2 <= len(pnf_with_type) - 2):
                            if (check_double_top_breakout(pnf_with_type, i + 2)):
                                trigger_list.append(("ascending_triple_top_breakout", i, 4))

                else:
                    if (check_double_bottom_breakdown(pnf_with_type, i)):
                        trigger_list.append(
                            ("double_bottom_breakdown", i, 2))  # If there is descending_triple_bottom, remove this

                        # Now check if there is descending triple bottom:
                        if (i + 2 <= len(pnf_with_type) - 2):
                            if (check_double_bottom_breakdown(pnf_with_type, i + 2)):
                                trigger_list.append(("descending_triple_bottom_breakdown", i, 4))

                                # Check for Triple top and bottom Also add spread triple top and bottom:
            if (i <= len(pnf_with_type) - 4):
                if (pnf_with_type.loc[i, "type"] == "X"):
                    if (check_triple_top_breakout(pnf_with_type, i)):
                        trigger_list.append(("triple_top_breakout", i, 4))
                    else:  # if we dont have triple top then check for spread triple top:
                        sp_res = check_spread_triple_top_breakout(pnf_with_type,
                                                                  i,
                                                                  spread_trigger_wide = self.spread_trigger_wide)
                        # observe for example True,5 is returned
                        if (sp_res[0]):
                            trigger_list.append(("spread_triple_top_breakout", i, sp_res[1]))
                else:
                    if (check_triple_bottom_breakdown(pnf_with_type, i)):
                        trigger_list.append(("triple_bottom_breakdown", i, 4))
                    else:  # if we dont have triple bottom then check for spread triple bottom:
                        sp_res = check_spread_triple_bottom_breakdown(pnf_with_type, i, spread_trigger_wide = self.spread_trigger_wide)
                        if (sp_res[0]):
                            trigger_list.append(("spread_triple_bottom_breakdown", i, sp_res[1]))

            # Check quadrople top and quadrople bottom triggers:
            if (i <= len(pnf_with_type) - 6):

                if (pnf_with_type.loc[i, "type"] == "X"):
                    if (check_quadruple_top_breakout(pnf_with_type, i)):
                        trigger_list.append(("quadruple_top_breakout", i, 6))
                else:
                    if (check_quadruple_bottom_breakdown(pnf_with_type, i)):
                        trigger_list.append(("quadruple_bottom_breakdown", i, 6))

                        # For ascending and descending triple top breakout, remove prev and after doubles.
        for trg in trigger_list:
            if (trg[0] == "ascending_triple_top_breakout"):
                if (('double_top_breakout', trg[1], 2) in trigger_list):
                    trigger_list.remove(('double_top_breakout', trg[1], 2))
                if (('double_top_breakout', trg[1] + 2, 2) in trigger_list):
                    trigger_list.remove(('double_top_breakout', trg[1] + 2, 2))

            if (trg[0] == "descending_triple_bottom_breakout"):
                if (('double_bottom_breakdown', trg[1], 2) in trigger_list):
                    trigger_list.remove(('double_bottom_breakdown', trg[1], 2))
                if (('double_bottom_breakdown', trg[1] + 2, 2) in trigger_list):
                    trigger_list.remove(('double_bottom_breakdown', trg[1] + 2, 2))

        return trigger_list


# Following functions are for bullish triggers:

def check_double_top_breakout(df, ind):
    return (df.loc[ind + 2, "close"] > df.loc[ind, "close"])


def check_triple_top_breakout(df, ind):
    ret = False
    if (df.loc[ind + 2, "close"] == df.loc[ind, "close"]):
        if (df.loc[ind + 4, "close"] > df.loc[ind, "close"]):
            ret = True

    return ret


def check_spread_triple_top_breakout(df, ind, spread_trigger_wide = 15):
    rule1 = df.loc[ind + 2, "close"] == df.loc[ind, "close"]
    rule2 = (df.loc[ind + 4, "close"] == df.loc[ind, "close"]) and (df.loc[ind + 2, "close"] < df.loc[ind, "close"])

    if (rule1 or rule2):
        lngth = 6
        while (((lngth + ind) < len(df)) and (lngth < spread_trigger_wide)):
            if (df.loc[lngth + ind, "close"] > df.loc[ind, "close"]):
                return True, lngth
            lngth += 2

    return False, 0


def check_ascending_triple_top_breakout(df, ind):
    # Handled as two multiple double_top_breakout so this is an unnecessary function
    return


def check_quadruple_top_breakout(df, ind):
    rule1 = df.loc[ind + 2, "close"] == df.loc[ind, "close"]
    rule2 = df.loc[ind + 4, "close"] == df.loc[ind, "close"]
    ret = False

    if (rule1 and rule2):
        if (df.loc[ind + 6, "close"] > df.loc[ind, "close"]):
            ret = True

    return ret


# Following functions are for bearish triggers:

def check_double_bottom_breakdown(df, ind):
    return (df.loc[ind + 2, "close"] < df.loc[ind, "close"])


def check_triple_bottom_breakdown(df, ind):
    ret = False
    if (df.loc[ind + 2, "close"] == df.loc[ind, "close"]):
        if (df.loc[ind + 4, "close"] < df.loc[ind, "close"]):
            ret = True

    return ret


def check_spread_triple_bottom_breakdown(df, ind, spread_trigger_wide = 15):
    rule1 = df.loc[ind + 2, "close"] == df.loc[ind, "close"]
    rule2 = (df.loc[ind + 4, "close"] == df.loc[ind, "close"]) and (df.loc[ind + 2, "close"] > df.loc[ind, "close"])

    if (rule1 or rule2):
        lngth = 6
        while (((lngth + ind) < len(df)) and (lngth<spread_trigger_wide)):
            if (df.loc[lngth + ind, "close"] < df.loc[ind, "close"]):
                return True, lngth
            lngth += 2

    return False, 0


def check_descending_triple_bottom_breakdown(df, ind):
    # Handled as two multiple double_bottom_breakdown so this is an unnecessary function
    return


def check_quadruple_bottom_breakdown(df, ind):
    rule1 = df.loc[ind + 2, "close"] == df.loc[ind, "close"]
    rule2 = df.loc[ind + 4, "close"] == df.loc[ind, "close"]
    ret = False
    if (rule1 and rule2):
        if (df.loc[ind + 6, "close"] < df.loc[ind, "close"]):
            ret = True

    return ret


if __name__ == '__main__':
    # Get the parameters:
    locale.setlocale(locale.LC_ALL, str('en_US.UTF-8'))
    msg = "Please enter the parameters.\n" \
          "Be careful with the format and leave the box empty to use default values (check readme file)."
    title = "PnF Trigger Parameters"

    fieldNames = ["Start date (format: yyyy-mm-dd)",
                  "End_date (format: yyyy-mm-dd)",
                  "Reversal amount (format: float)",
                  "Box size (format: float)",
                  "Last n days for triggers (format: int)",
                  "spread_trigger_wide (format: int)",
                  "Would you like to download data? (format: yes/no)"]

    fieldValues = easygui.multenterbox(msg, title, fieldNames)
    if fieldValues is None:
        sys.exit(0)

    #Fix the format of parameters:

    start_date = str(fieldValues[0]).strip()
    if (start_date == ""):
        start_date = "2021-01-01"

    end_date = str(fieldValues[1]).strip()
    if (end_date == ""):
        end_date = str(dt.date.today())

    reversal_amount = str(fieldValues[2]).strip()
    if (reversal_amount == ""):
        reversal_amount = 3
    else:
        reversal_amount = float(reversal_amount)

    box_size = str(fieldValues[3]).strip()
    if (box_size == ""):
        box_size = None
    else:
        box_size = float(box_size)

    last_n_days = str(fieldValues[4]).strip()
    start = dt.datetime.strptime(start_date, "%Y-%m-%d").date()
    end = dt.datetime.strptime(end_date, "%Y-%m-%d").date()
    if (last_n_days == ""):
        last_n_days = (end - start).days
    else:
        last_n_days = int(last_n_days)

    spread_trigger_wide = str(fieldValues[5]).strip()
    if (spread_trigger_wide == ""):
        spread_trigger_wide = 15
    else:
        spread_trigger_wide = float(spread_trigger_wide)

    first_date_for_trigger = end - dt.timedelta(days = last_n_days)

    get_data = str(fieldValues[6]).strip().lower()

    if (get_data == ""):
        get_data = "yes"
    if (get_data=="yes"):
        get_data=True
    else:
        get_data=False


    txt_file = open("tickers.txt", 'r')
    content = txt_file.read()
    txt_file.close()
    ticker_list = content.split()
    pnf_obj_dic = {}
    for i in ticker_list:
        pnf_obj_dic[i] = PnfAnalysis(i,
                                     start_date=start_date,
                                     end_date=end_date,
                                     reversal_amount=reversal_amount,
                                     box_size=box_size,
                                     last_n_days=last_n_days,
                                     spread_trigger_wide=spread_trigger_wide,
                                     get_data=get_data)

    #Now get the triggers for each stock and store them in a dictionary:
    stock_triggers = {}

    for i in pnf_obj_dic:
        temp_trig_list = pnf_obj_dic[i].check_triggers()
        temp_pnf_data = pnf_obj_dic[i].pnf_data
        date_list = pnf_obj_dic[i].closing_dates_list

        #Calculate the first_date_col_number:
        my_date = date_list[0]
        first_date_col_number = 1
        while my_date < first_date_for_trigger:
            first_date_col_number += 1
            my_date = date_list[first_date_col_number]

        #Calculate last column of pnf data_to use:

        final_temp_trig_list = list(temp_trig_list)
        for j in temp_trig_list:
            pnf_col_num = j[1]
            pnf_wide = j[2]
            if (date_list[pnf_col_num + pnf_wide - 1] < first_date_for_trigger): #If before triggering date, drop the trigger
                final_temp_trig_list.remove(j)
                first_date_col_number = pnf_col_num + pnf_wide + 1 # Find the column of -15th day

            elif (pnf_col_num + pnf_wide == first_date_col_number):

                temp_data = pnf_obj_dic[i].data
                price_level = temp_pnf_data.loc[pnf_col_num, "close"] #This keeps the price level of trigger
                try:
                    temp_min = temp_data.loc[first_date_for_trigger, "Low"]
                    temp_max = temp_data.loc[first_date_for_trigger, "High"]
                    my_bool = (price_level < temp_max) and (price_level > temp_min)
                except:
                    my_bool = True
                
                if my_bool == False:
                    final_temp_trig_list.remove(j)

        # add the trigger list to dictionary
        if final_temp_trig_list != []:
            stock_triggers[i] = final_temp_trig_list


    #Now display the bearish and bullish triggers.

    bullish_names = ["double_top_breakout", "ascending_triple_top_breakout", "triple_top_breakout", "spread_triple_top_breakout", "quadruple_top_breakout"]
    bearish_names = ["double_bottom_breakdown", "descending_triple_bottom_breakdown", "triple_bottom_breakdown", "spread_triple_bottom_breakdown", "quadruple_bottom_breakdown"]

    bullish_trigger_str = "   "
    bearish_trigger_str = "   "
    for i in stock_triggers:
        for j in stock_triggers[i]:
            if j[0] in bullish_names:
                bullish_trigger_str = bullish_trigger_str + i + " - " + j[0] + " at column " + str(j[1]) + " in the graph" + "\n" + "   "
            else:
                bearish_trigger_str = bearish_trigger_str + i + " - " + j[0] + " at column " + str(j[1]) + " in the graph" + "\n" + "   "

    #Write triggers to a txt file:
    triggers_txt = "Bullish triggers:" + "\n" + bullish_trigger_str + "\n\n" + "Bearish triggers:"  "\n" + bearish_trigger_str +  "\n\n" 
    tr_file_path = "trigger_lists/triggers_{}.txt".format(str(dt.datetime.today())[:-7]).replace(":", "_").replace("-", "_").replace(" ", "_")
    print(triggers_txt.split("\n"))

    with open(tr_file_path, 'w') as f:
        f.write(triggers_txt)

    text = "Trigger list is created at trigger_lists file in the directory with the name of {} \n Enter the ticker of stock you would like to plot:".format(tr_file_path)
    title = "PnF Triggers"

    # Ask the user to plot.
    while 1:
        output = easygui.enterbox(text, title)
        if output is None:
            sys.exit()

        lines = [] #Format: ( x_start, x_end, y_start, y_end )
        temp_triggers = stock_triggers[output]
        temp_pnf_data = pnf_obj_dic[output].pnf_data

        for i in temp_triggers:
            x_start = i[1]
            x_end = i[1] + i[2]
            y_start = temp_pnf_data.loc[x_start, "close"]
            y_end = y_start
            lines.append((x_start, x_end, y_start, y_end))

        pnf_obj_dic[output].create_plot_from_pnf_data(figure_size=(12, 6),
                                   chart_name=output,
                                   grid_freq_y=5,
                                   grid_freq_x=5,
                                    lines = lines)
