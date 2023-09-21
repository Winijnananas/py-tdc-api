#!/bin/bash

echo "Building PyMuPDF..."
pip install --no-binary :all: PyMuPDF

echo "Building reportlab..."
pip install --no-binary :all: reportlab