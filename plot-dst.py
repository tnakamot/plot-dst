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

def cache_file_path(year, month, cache_dir = Path('cache')):
    '''
    Returns the cache file path of the DST data for the given year and month.
    '''
    
    return cache_dir / f'{year:04d}{month:02d}.html'

def download_dst_data(year, month, cache_file):
    '''
    Download DST index data from WDC for Geomagnetism, Kyoto to the specified file.
    '''

    cache_file.parent.mkdir(parents = True, exist_ok = True)

    url = f'https://wdc.kugi.kyoto-u.ac.jp/dst_final/{year:04d}{month:02d}/index-j.html'
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f'Failed to download data from {url}')

    with open(cache_file, 'wb') as f:
        f.write(response.content)

    print(f'Downloaded DST index data to {cache_file}.')

def parse_dst_data_file(data_file, year, month):
    '''
    Parse the DST index data in the HTML file from WDC for Geomagnetism, Kyoto.
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
    cache_file = cache_file_path(year, month, cache_dir)
    if not cache_file.is_file():
        download_dst_data(year, month, cache_file)

    return parse_dst_data_file(cache_file, year, month)
    
def parse_arguments():
    parser = argparse.ArgumentParser(
        description = 'Tool to plot DST (Disturbance Storm Time) Index.')

    date_type = lambda s: datetime.strptime(s, '%Y-%m-%d').date()

    # Argument definition.
    parser.add_argument('--cache-dir',
                        dest    = 'cache_dir',
                        type    = Path,
                        metavar = 'DIR',
                        default = 'cache',
                        help    = 'Cache directory to store downloaded DST data. (default: %(default)s)')
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
                        default = plt.rcParams.get('figure.figsize')[1],
                        help    = 'Height of plot in inches. (default: %(default)s)')
    parser.add_argument('--dpi',
                        type    = float,
                        dest    = 'dpi',
                        metavar = 'DPI',
                        default = plt.rcParams.get('figure.dpi'),
                        help    = 'DPI for plotting. (default: %(default)s)')
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


    fig = plt.figure(figsize = (args.width, args.height), dpi = args.dpi)
    ax1 = fig.add_subplot(1, 1, 1)
    ax1.plot(time_array, dst_array)
    ax1.set_ylabel('Dst (Disturbance Storm Time) [nT]')
    
    datetime_formatter = mdates.DateFormatter('%Y-%m-%d')
    ax1.xaxis.set_major_formatter(datetime_formatter)
    ax1.set_xlim(args.start_date, args.end_date)

    if args.show_plot:
        plt.show()

if __name__ == "__main__":
    main()
