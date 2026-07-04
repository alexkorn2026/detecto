#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Detecto - Log-Datei Scanner fuer kritische/personenbezogene Daten
# MIT License - Copyright (c) 2026 Alexander Kornbrust
#
# Wrapper fuer Rueckwaertskompatibilitaet.
# Verwendung: python3 detecto_cli.py test.log --full
# Alternative: PYTHONPATH=src python3 -m detecto test.log --full
# Oder nach Installation: pip install -e . && detecto test.log

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

# Verhindere dass dieses Skript als Package-Modul geladen wird
if __name__ == "__main__":
    from detecto.cli import main
    main()
