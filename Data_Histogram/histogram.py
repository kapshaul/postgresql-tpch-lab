import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter

# List of items with their index, key name, and associated table
items = [
    # Q9
    (0, 'ps_partkey', 'partsupp'),
    (1, 'l_partkey', 'lineitem'),
    # Q10
    (0, 'c_custkey', 'customer'),
    (1, 'o_custkey', 'order'),
    # Q11 - Modified
    (4, 'o_orderdate', 'order'),
    (10, 'l_shipdate', 'lineitem'),
    # Q12
    (0, 'o_orderkey', 'order'),
    (0, 'l_orderkey', 'lineitem'),
    # Q15
    (0, 's_suppkey', 'supplier'),
    (2, 'l_suppkey', 'lineitem'),
]

z_val = ['z0', 'z1', 'z1_5']

# Define the number of rows to plot histogram
row_n = 200000

# Function to determine if the entire column is numeric or not
def is_column_numeric(series):
    # Check if the first value is numeric; assume consistency for the whole column
    try:
        float(series.iloc[0])
        return True
    except ValueError:
        return False


# Looping through each item in the 'items' list
for column, key, table in items:

    # Looping through different distribution
    for z in z_val:        
        # Define the file path
        file_path = '/data/leeyongh-psql/Data/TPC-H/' + z + '/' + table + '.tbl'
        output_dir = './' + z

        print("Start, " + key + '_' + z)
        
        # Load the TBL file with '|' delimiter and no header
        data = pd.read_csv(file_path, delimiter='|', header=None)
        # Select the column data up to the defined number of rows
        column_c = data[column][:row_n]

        # Determine if the column is numeric
        hist_data = []
        if is_column_numeric(column_c):
            # Convert entire column to numeric
            hist_data = column_c.astype(float)
            unique_values = np.unique(hist_data)
        else:
            # Handle as string data
            hist_data = column_c
            unique_values = int(len(set(hist_data)))

        # Create the directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        plt.figure()
        plt.hist(hist_data, bins=unique_values, edgecolor='k')
        plt.ylabel('Frequency')
        plt.xlabel('Values')
        plt.title(key + '_' + z)

        plt.savefig(output_dir + '/' + key + '_' + z + '.png')
        print("Complete, " + key + '_' + z)