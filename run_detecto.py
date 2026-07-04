#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Detecto - Log-Datei Scanner fuer kritische/personenbezogene Daten
#
# MIT License - Copyright (c) 2026 Alexander Kornbrust
#
# Wrapper-Skript fuer Rueckwaertskompatibilitaet.
# Das eigentliche Package liegt in src/detecto/.

import sys
import os

# src/ zum Python-Path hinzufuegen
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from detecto.cli import main

if __name__ == "__main__":
    main()
