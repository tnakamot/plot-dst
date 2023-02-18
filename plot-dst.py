#!/usr/bin/env python3

import argparse
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import os
from pathlib import Path
import requests

from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.style.use(os.path.join(os.path.dirname(__file__), 'mplstyle'))

def dst_cache_file_path(year, month, cache_dir = Path('cache')):
    '''
    Returns the cache file path of the Dst data for the given year and month.
    '''
    
    return cache_dir / f'{year:04d}{month:02d}.html'

def download_dst_data(year, month, cache_file):
    '''
    Download Dst index data from WDC for Geomagnetism, Kyoto to the specified file.
    '''

    cache_file.parent.mkdir(parents = True, exist_ok = True)

    url = f'https://wdc.kugi.kyoto-u.ac.jp/dst_final/{year:04d}{month:02d}/index-j.html'
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f'Failed to download data from {url}')

    with open(cache_file, 'wb') as f:
        f.write(response.content)

    print(f'Downloaded Dst index data to {cache_file}.')

def parse_dst_data_file(data_file, year, month):
    '''
    Parse the Dst index data in the HTML file from WDC for Geomagnetism, Kyoto.
    '''

    with open(data_file, 'rb') as f:
        root = BeautifulSoup(f.read(), 'html.parser')
    elements = root.find_all('pre', {'class': 'data'})
    if len(elements) > 1:
        raise Exception(f'Multiple <pre class="data"> is found in {data_file}.')
    if len(elements) == 0:
        raise Exception(f'No <pre class="data"> is found in {data_file}.')

    time_array = []
    dst_array  = []

    data_section = False
    for line in elements[0].text.split('\n'):
        if line.strip() == 'DAY':
            data_section = True
            continue

        if data_section and line.strip() != '':
            # Extract day of the month
            day = int(line[0:2])
            for hour in range(1, 24 + 1):
                if hour <= 8:
                    start_index = hour * 4 - 1
                elif hour <= 16:
                    start_index = hour * 4
                else:
                    start_index = hour * 4 + 1
                end_index = start_index + 4
                dst = int(line[start_index:end_index])

                if hour == 24:
                    time = datetime(year = year, month = month, day = day, hour = 0)
                    time = time + relativedelta(days = 1)
                else:
                    time = datetime(year = year, month = month, day = day, hour = hour)

                time_array.append(time)
                dst_array.append(dst)

    return time_array, dst_array

def get_dst_data(year, month, cache_dir):
    # Download the data of that year and month if it does not exist in the
    # cache directory.
    cache_file = dst_cache_file_path(year, month, cache_dir)
    if not cache_file.is_file():
        download_dst_data(year, month, cache_file)

    return parse_dst_data_file(cache_file, year, month)

def download_sunspot_data(cache_file):
    '''
    Download sunspot data from NAOJ.
    '''

    cache_file.parent.mkdir(parents = True, exist_ok = True)

    url = 'https://solarwww.mtk.nao.ac.jp/mitaka_solar/data03/sunspots/number/mtkmonthly.txt'
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f'Failed to download data from {url}')

    with open(cache_file, 'w') as f:
        f.write(response.text)

    print(f'Downloaded sunspot data to {cache_file}.')

def parse_sunspot_data_file(data_file):
    '''
    Parse the sunspot data in text from NAOJ.
    '''
    with open(data_file, 'r') as f:
        lines = f.readlines()


    time_array = []
    raw_array  = []
    smoothed_array = []

    for line in lines:
        if (line.startswith(' 19') or line.startswith(' 20')) and len(line) > 8 and line[7] == ' ':
            # data format is explained here:
            #  https://solarwww.mtk.nao.ac.jp/mitaka_solar/data03/sunspots/number/info_data_j.txt 
            year     = int(line[1:5])
            month    = int(line[8:10])
            
            raw_str = line[40:46]
            smoothed_str = line[66:72]
            if len(raw_str.strip()) == 0 or len(smoothed_str.strip()) == 0:
                continue
            
            raw      = float(raw_str)
            smoothed = float(smoothed_str)

            time_array.append(date(year, month, 1))
            raw_array.append(raw)
            smoothed_array.append(smoothed)

    return time_array, raw_array, smoothed_array
    
def get_sunspot_data(cache_dir):
    cache_file = cache_dir / 'mtkmonthly.txt'
    if not cache_file.is_file():
        download_sunspot_data(cache_file)

    return parse_sunspot_data_file(cache_file)
    
def parse_arguments():
    parser = argparse.ArgumentParser(
        description = 'Tool to plot Dst (Disturbance Storm Time) Index.')

    date_type = lambda s: datetime.strptime(s, '%Y-%m-%d').date()

    # Argument definition.
    parser.add_argument('--output-file',
                        dest    = 'output_file',
                        type    = Path,
                        metavar = 'OUT',
                        default = 'Dst.png',
                        help    = 'Output image file of the Dst time history plot. (default: %(default)s)')
    parser.add_argument('--start-date',
                        dest    = 'start_date',
                        type    = date_type,
                        metavar = 'DATE',
                        default = date(1957, 1, 1),
                        help    = 'Start date of the plot. (default: %(default)s)')
    parser.add_argument('--end-date',
                        dest    = 'end_date',
                        type    = date_type,
                        metavar = 'DATE',
                        default = date(1957, 12, 31),
                        help    = 'End date of the plot. (default: %(default)s)')
    parser.add_argument('--cache-dir',
                        dest    = 'cache_dir',
                        type    = Path,
                        metavar = 'DIR',
                        default = 'cache',
                        help    = 'Cache directory to store downloaded DST data. (default: %(default)s)')
    parser.add_argument('--width',
                        type    = float,
                        dest    = 'width',
                        metavar = 'WIDTH',
                        default = plt.rcParams.get('figure.figsize')[0],
                        help    = 'Width of plot in inches. (default: %(default)s)')
    parser.add_argument('--height',
                        type    = float,
                        dest    = 'height',
                        metavar = 'HEIGHT',
                        default = plt.rcParams.get('figure.figsize')[1] * 1.5,
                        help    = 'Height of plot in inches. (default: %(default)s)')
    parser.add_argument('--dpi',
                        type    = float,
                        dest    = 'dpi',
                        metavar = 'DPI',
                        default = plt.rcParams.get('figure.dpi'),
                        help    = 'DPI for plotting. (default: %(default)s)')
    parser.add_argument('--plot-sunspot',
                        dest    = 'plot_sunspot',
                        action  = 'store_true',
                        help    = 'Plot sunspot relative number.')
    parser.add_argument('--show-plot',
                        dest    = 'show_plot',
                        action  = 'store_true',
                        help    = 'Show the plot in GUI.')
    
    # Actually parse the arguments.
    args = parser.parse_args()

    # Sanity checks.
    if args.start_date >= args.end_date:
        raise Exception(f'Start date (--start-date) must be earlier than end date (--end-date).')
    
    return args

def plot_dst(ax, time_array, dst_array, start_date, end_date):
    ax.plot(time_array, dst_array)
    ax.set_ylabel('Dst (Disturbance Storm Time) [nT]')
    
    datetime_formatter = mdates.DateFormatter('%Y-%m-%d')
    ax.xaxis.set_major_formatter(datetime_formatter)
    ax.set_xlim(start_date, end_date)

def plot_sunspot(ax, time_array, raw_array, smoothed_array, start_date, end_date):
    ax.plot(time_array, raw_array, color = 'black', label = 'Monthly Raw')
    ax.plot(time_array, smoothed_array, color = 'green', label = '13-Month Moving Average')
    
    ax.set_ylabel('Sunspot Relative Number')
    
    datetime_formatter = mdates.DateFormatter('%Y-%m-%d')
    ax.xaxis.set_major_formatter(datetime_formatter)
    ax.set_xlim(start_date, end_date)

    ax.legend(loc = 'upper right')

def main():
    args = parse_arguments()

    # Download and parse DST data.
    first_month = args.start_date.replace(day = 1)
    end_month   = args.end_date.replace(day = 1)
    current_date = first_month
    time_array = []
    dst_array  = []
    while current_date <= end_month:
        time_new, dst_new =  get_dst_data(
            year = current_date.year,
            month = current_date.month,
            cache_dir = args.cache_dir)

        time_array.extend(time_new)
        dst_array.extend(dst_new)
        
        current_date = current_date + relativedelta(months = 1)
       
    # Plot Dst index time history.
    ax_num = 2 if args.plot_sunspot else 1
    
    fig = plt.figure(figsize = (args.width, args.height), dpi = args.dpi)
    ax1 = fig.add_subplot(ax_num, 1, 1)
    plot_dst(ax1, time_array, dst_array, args.start_date, args.end_date + relativedelta(days = 1))
    
    # Plot sunspot relative number.
    sunspot_time_array, sunspot_raw_array, sunspot_smoothed_array = get_sunspot_data(args.cache_dir)
    if args.plot_sunspot:
        ax2 = fig.add_subplot(2, 1, 2)
        plot_sunspot(ax2,
                     sunspot_time_array,
                     sunspot_raw_array,
                     sunspot_smoothed_array,
                     args.start_date,
                     args.end_date + relativedelta(days = 1))

    plt.savefig(args.output_file)
    print(f'Generated the Dst plot in {args.output_file}.')

    if args.show_plot:
        plt.show()

if __name__ == "__main__":
    main()
