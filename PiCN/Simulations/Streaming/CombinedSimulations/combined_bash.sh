#!/bin/bash
python3 RunThreeLayerSimulationCombinedStream.py placeholder
python3 RunThreeLayerSimulationCombinedClassic.py placeholder
python3 RunSixLayerSimulationCombinedStream.py placeholder
python3 RunSixLayerSimulationCombinedClassic.py placeholder
python3 create_plot_combined.py placeholder
