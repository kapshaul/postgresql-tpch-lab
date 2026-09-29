#!/bin/bash

# Specify the directory where the .tbl files are located
directory="/data/leeyongh-psql/Data/TPC-H-Skew/test"

# Array of .tbl files
files=("customer.tbl" "lineitem.tbl" "order.tbl" "part.tbl" "partsupp.tbl" "supplier.tbl")

z_vals=("z0" "z1" "z1_5")

# Loop through each file
for file in "${files[@]}"; do

    for z in "${z_vals[@]}"; do
        filepath="$directory/$z/$file"

        # Check if the file exists
        if [ -f "$filepath" ]; then
            echo "Shuffling $file with $z..."
            # Shuffle the file and overwrite the original file
            shuf "$filepath" -o "$filepath"
            echo "$file has been shuffled and overwritten."
        else
            echo "$file does not exist in $directory."
        fi
    done
done

echo "Shuffling complete for all files."
