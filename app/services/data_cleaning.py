"""
Service de préparation et nettoyage des données (F1-UC2)

Ce module fournit des fonctionnalités pour :
- Charger des fichiers JSON/NDJSON
- Nettoyer les valeurs manquantes (NaN, null, chaînes vides)
- Convertir les types de données
- Supprimer les doublons
- Détecter et gérer les outliers
- Valider les plages de valeurs
"""

import json
import os
from pathlib import Path
from typing import Any
from datetime import datetime
import statistics
import math


class DataCleaningService:
    """Service pour le nettoyage et la préparation des données."""
    
    # Schéma par défaut pour les données ClimaTrack
    DEFAULT_SCHEMA = {
        "timestamp": "datetime",
        "ID": "str",
        "type": "str",
        "temperature": "float",
        "humidity": "float",
        "TVOC": "float",
        "CO2": "float",
        "PM1.0": "float",
        "PM2.5": "float",
        "PM10": "float",
        "sound_level": "float"
    }
    
    # Plages de validation par défaut pour la qualité de l'air
    DEFAULT_VALIDATION_RULES = {
        "temperature": (-40.0, 60.0),      # °C
        "humidity": (0.0, 100.0),           # %
        "TVOC": (0.0, 60000.0),             # ppb
        "CO2": (0.0, 10000.0),              # ppm
        "PM1.0": (0.0, 1000.0),             # µg/m³
        "PM2.5": (0.0, 1000.0),             # µg/m³
        "PM10": (0.0, 1000.0),              # µg/m³
        "sound_level": (0.0, 150.0)         # dB
    }
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialise le service de nettoyage.
        
        Args:
            data_dir: Répertoire contenant les fichiers de données
        """
        self.data_dir = Path(data_dir)
    
    def load_ndjson(self, filename: str) -> list[dict]:
        """
        Charge un fichier NDJSON (Newline Delimited JSON).
        
        Args:
            filename: Nom du fichier à charger
            
        Returns:
            Liste de dictionnaires
        """
        filepath = self.data_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Fichier non trouvé: {filepath}")
        
        data = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"Erreur ligne {line_num}: {e}")
        
        return data
    
    def load_json(self, filename: str) -> dict | list:
        """
        Charge un fichier JSON standard.
        
        Args:
            filename: Nom du fichier à charger
            
        Returns:
            Données JSON
        """
        filepath = self.data_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Fichier non trouvé: {filepath}")
        
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def load_data(self, filename: str) -> list[dict]:
        """
        Charge les données depuis un fichier (détection auto du format).
        
        Args:
            filename: Nom du fichier à charger
            
        Returns:
            Liste de dictionnaires
        """
        filepath = self.data_dir / filename
        
        # Essayer NDJSON d'abord
        try:
            return self.load_ndjson(filename)
        except json.JSONDecodeError:
            pass
        
        # Essayer JSON standard
        data = self.load_json(filename)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "data" in data:
            return data["data"]
        else:
            return [data]
    
    def save_cleaned_data(
        self,
        data: list[dict],
        filename: str,
        format: str = "ndjson"
    ) -> str:
        """
        Sauvegarde les données nettoyées.
        
        Args:
            data: Données à sauvegarder
            filename: Nom du fichier de sortie
            format: "ndjson" ou "json"
            
        Returns:
            Chemin du fichier créé
        """
        # Créer le dossier cleaned s'il n'existe pas
        cleaned_dir = self.data_dir / "cleaned"
        cleaned_dir.mkdir(exist_ok=True)
        
        filepath = cleaned_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            if format == "ndjson":
                for record in data:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            else:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def _is_nan(self, value: Any) -> bool:
        """Vérifie si une valeur est NaN ou manquante."""
        if value is None:
            return True
        if isinstance(value, str):
            return value.lower() in ("nan", "null", "none", "na", "n/a", "")
        if isinstance(value, float):
            return math.isnan(value)
        return False
    
    def _convert_value(self, value: Any, target_type: str) -> Any:
        """
        Convertit une valeur vers le type cible.
        
        Args:
            value: Valeur à convertir
            target_type: Type cible ("int", "float", "str", "bool", "datetime")
            
        Returns:
            Valeur convertie ou None si échec
        """
        if self._is_nan(value):
            return None
        
        try:
            if target_type == "int":
                return int(float(value))
            elif target_type == "float":
                return float(value)
            elif target_type == "str":
                return str(value)
            elif target_type == "bool":
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes", "oui")
                return bool(value)
            elif target_type == "datetime":
                if isinstance(value, str):
                    # Parser ISO format
                    return value  # Garder comme string ISO
                return str(value)
            else:
                return value
        except (ValueError, TypeError):
            return None
    
    def convert_types(
        self,
        data: list[dict],
        schema: dict[str, str] | None = None
    ) -> list[dict]:
        """
        Convertit les types de données selon un schéma.
        
        Args:
            data: Données à convertir
            schema: {"colonne": "type"} - utilise DEFAULT_SCHEMA si None
            
        Returns:
            Données avec types convertis
        """
        schema = schema or self.DEFAULT_SCHEMA
        
        result = []
        for record in data:
            converted = {}
            for key, value in record.items():
                if key in schema:
                    converted[key] = self._convert_value(value, schema[key])
                else:
                    converted[key] = value
            result.append(converted)
        
        return result
    
    def remove_duplicates(
        self,
        data: list[dict],
        keys: list[str] | None = None
    ) -> tuple[list[dict], int]:
        """
        Supprime les enregistrements dupliqués.
        
        Args:
            data: Données à dédupliquer
            keys: Colonnes à utiliser pour identifier les doublons
                  (None = toutes les colonnes)
            
        Returns:
            Tuple (données sans doublons, nombre de doublons supprimés)
        """
        if not data:
            return [], 0
        
        seen = set()
        result = []
        duplicates = 0
        
        for record in data:
            if keys:
                # Utiliser uniquement les clés spécifiées
                key_tuple = tuple(record.get(k) for k in keys)
            else:
                # Utiliser toutes les valeurs
                key_tuple = tuple(sorted(
                    (k, str(v)) for k, v in record.items()
                ))
            
            if key_tuple not in seen:
                seen.add(key_tuple)
                result.append(record)
            else:
                duplicates += 1
        
        return result, duplicates
    
    def handle_missing_values(
        self,
        data: list[dict],
        strategy: str = "remove",
        columns: list[str] | None = None,
        fill_value: Any = None,
        numeric_strategy: str = "mean"
    ) -> tuple[list[dict], dict]:
        """
        Gère les valeurs manquantes.
        
        Args:
            data: Données à traiter
            strategy: "remove" (supprimer lignes) ou "fill" (remplacer)
            columns: Colonnes à vérifier (None = toutes)
            fill_value: Valeur de remplacement pour stratégie "fill"
            numeric_strategy: Pour colonnes numériques - "mean", "median", "zero"
            
        Returns:
            Tuple (données traitées, statistiques)
        """
        if not data:
            return [], {"removed": 0, "filled": 0}
        
        columns = columns or list(data[0].keys())
        stats = {"removed": 0, "filled": 0, "missing_by_column": {}}
        
        # Compter les valeurs manquantes par colonne
        for col in columns:
            missing_count = sum(1 for r in data if self._is_nan(r.get(col)))
            stats["missing_by_column"][col] = missing_count
        
        if strategy == "remove":
            result = []
            for record in data:
                has_missing = any(
                    self._is_nan(record.get(col))
                    for col in columns
                )
                if not has_missing:
                    result.append(record)
                else:
                    stats["removed"] += 1
            return result, stats
        
        elif strategy == "fill":
            # Calculer les statistiques pour les colonnes numériques
            numeric_fill_values = {}
            for col in columns:
                values = [
                    r[col] for r in data
                    if col in r 
                    and not self._is_nan(r[col])
                    and isinstance(r[col], (int, float))
                ]
                
                if values:
                    if numeric_strategy == "mean":
                        numeric_fill_values[col] = statistics.mean(values)
                    elif numeric_strategy == "median":
                        numeric_fill_values[col] = statistics.median(values)
                    elif numeric_strategy == "zero":
                        numeric_fill_values[col] = 0.0
            
            result = []
            for record in data:
                new_record = record.copy()
                for col in columns:
                    if self._is_nan(new_record.get(col)):
                        if col in numeric_fill_values:
                            new_record[col] = round(numeric_fill_values[col], 2)
                        elif fill_value is not None:
                            new_record[col] = fill_value
                        stats["filled"] += 1
                result.append(new_record)
            
            return result, stats
        
        return data, stats
    
    def remove_outliers(
        self,
        data: list[dict],
        columns: list[str],
        method: str = "iqr",
        threshold: float = 1.5
    ) -> tuple[list[dict], dict]:
        """
        Supprime les valeurs aberrantes (outliers).
        
        Args:
            data: Données à traiter
            columns: Colonnes numériques à vérifier
            method: "iqr" (Interquartile Range) ou "zscore"
            threshold: Seuil (1.5 pour IQR, 3.0 pour z-score)
            
        Returns:
            Tuple (données sans outliers, statistiques)
        """
        if not data or not columns:
            return data, {"removed": 0, "outliers_by_column": {}}
        
        # Calculer les bornes pour chaque colonne
        bounds = {}
        stats = {"removed": 0, "outliers_by_column": {}}
        
        for col in columns:
            values = [
                r[col] for r in data
                if col in r 
                and r[col] is not None
                and isinstance(r[col], (int, float))
            ]
            
            if len(values) < 4:  # Pas assez de données
                continue
            
            sorted_values = sorted(values)
            n = len(sorted_values)
            
            if method == "iqr":
                q1_idx = n // 4
                q3_idx = (3 * n) // 4
                q1 = sorted_values[q1_idx]
                q3 = sorted_values[q3_idx]
                iqr = q3 - q1
                bounds[col] = (q1 - threshold * iqr, q3 + threshold * iqr)
            
            elif method == "zscore":
                mean = statistics.mean(values)
                std = statistics.stdev(values) if len(values) > 1 else 0
                if std > 0:
                    bounds[col] = (mean - threshold * std, mean + threshold * std)
        
        # Filtrer les outliers
        result = []
        for record in data:
            is_outlier = False
            outlier_cols = []
            
            for col, (lower, upper) in bounds.items():
                if col in record and record[col] is not None:
                    if isinstance(record[col], (int, float)):
                        if record[col] < lower or record[col] > upper:
                            is_outlier = True
                            outlier_cols.append(col)
            
            if not is_outlier:
                result.append(record)
            else:
                stats["removed"] += 1
                for col in outlier_cols:
                    stats["outliers_by_column"][col] = \
                        stats["outliers_by_column"].get(col, 0) + 1
        
        return result, stats
    
    def validate_ranges(
        self,
        data: list[dict],
        rules: dict[str, tuple[float, float]] | None = None
    ) -> tuple[list[dict], list[dict], dict]:
        """
        Valide que les valeurs sont dans les plages attendues.
        
        Args:
            data: Données à valider
            rules: {"colonne": (min, max)} - utilise DEFAULT_VALIDATION_RULES si None
            
        Returns:
            Tuple (données valides, données invalides, statistiques)
        """
        rules = rules or self.DEFAULT_VALIDATION_RULES
        
        valid = []
        invalid = []
        stats = {"valid": 0, "invalid": 0, "invalid_by_column": {}}
        
        for record in data:
            is_valid = True
            invalid_cols = []
            
            for col, (min_val, max_val) in rules.items():
                if col in record and record[col] is not None:
                    if isinstance(record[col], (int, float)):
                        if record[col] < min_val or record[col] > max_val:
                            is_valid = False
                            invalid_cols.append(col)
            
            if is_valid:
                valid.append(record)
                stats["valid"] += 1
            else:
                invalid.append(record)
                stats["invalid"] += 1
                for col in invalid_cols:
                    stats["invalid_by_column"][col] = \
                        stats["invalid_by_column"].get(col, 0) + 1
        
        return valid, invalid, stats
    
    def get_statistics(self, data: list[dict], columns: list[str] | None = None) -> dict:
        """
        Calcule des statistiques descriptives sur les données.
        
        Args:
            data: Données à analyser
            columns: Colonnes numériques (None = auto-détection)
            
        Returns:
            Statistiques par colonne
        """
        if not data:
            return {}
        
        # Auto-détection des colonnes numériques si non spécifié
        if columns is None:
            columns = []
            for key, value in data[0].items():
                if isinstance(value, (int, float)) and value is not None:
                    columns.append(key)
        
        stats = {}
        
        for col in columns:
            values = [
                r[col] for r in data
                if col in r 
                and r[col] is not None
                and isinstance(r[col], (int, float))
            ]
            
            if not values:
                continue
            
            stats[col] = {
                "count": len(values),
                "missing": len(data) - len(values),
                "min": round(min(values), 4),
                "max": round(max(values), 4),
                "mean": round(statistics.mean(values), 4),
                "median": round(statistics.median(values), 4),
                "std": round(statistics.stdev(values), 4) if len(values) > 1 else 0
            }
        
        return stats
    
    def clean_dataset(
        self,
        filename: str,
        config: dict | None = None
    ) -> dict:
        """
        Pipeline complet de nettoyage d'un dataset.
        
        Args:
            filename: Nom du fichier à nettoyer
            config: Configuration du nettoyage
            
        Returns:
            Rapport de nettoyage avec données nettoyées
        """
        config = config or {}
        
        # Charger les données
        data = self.load_data(filename)
        original_count = len(data)
        
        report = {
            "filename": filename,
            "original_count": original_count,
            "timestamp": datetime.now().isoformat(),
            "steps": []
        }
        
        # Étape 1: Conversion des types
        schema = config.get("schema", self.DEFAULT_SCHEMA)
        data = self.convert_types(data, schema)
        report["steps"].append({
            "step": "convert_types",
            "schema_applied": list(schema.keys())
        })
        
        # Étape 2: Suppression des doublons
        if config.get("remove_duplicates", True):
            duplicate_keys = config.get("duplicate_keys", ["timestamp", "ID"])
            data, dup_count = self.remove_duplicates(data, keys=duplicate_keys)
            report["steps"].append({
                "step": "remove_duplicates",
                "keys_used": duplicate_keys,
                "duplicates_removed": dup_count,
                "remaining": len(data)
            })
        
        # Étape 3: Gestion des valeurs manquantes
        missing_strategy = config.get("missing_strategy", "fill")
        missing_columns = config.get("missing_columns", [
            "temperature", "humidity", "TVOC", "CO2", "sound_level"
        ])
        numeric_strategy = config.get("numeric_strategy", "median")
        
        data, missing_stats = self.handle_missing_values(
            data,
            strategy=missing_strategy,
            columns=missing_columns,
            numeric_strategy=numeric_strategy
        )
        report["steps"].append({
            "step": "handle_missing_values",
            "strategy": missing_strategy,
            "numeric_strategy": numeric_strategy,
            "stats": missing_stats,
            "remaining": len(data)
        })
        
        # Étape 4: Validation des plages
        if config.get("validate_ranges", True):
            validation_rules = config.get("validation_rules", self.DEFAULT_VALIDATION_RULES)
            data, invalid_data, valid_stats = self.validate_ranges(data, validation_rules)
            report["steps"].append({
                "step": "validate_ranges",
                "rules_applied": list(validation_rules.keys()),
                "stats": valid_stats,
                "remaining": len(data)
            })
        
        # Étape 5: Suppression des outliers (optionnel)
        if config.get("remove_outliers", False):
            outlier_columns = config.get("outlier_columns", [
                "temperature", "humidity", "TVOC", "CO2"
            ])
            outlier_method = config.get("outlier_method", "iqr")
            outlier_threshold = config.get("outlier_threshold", 1.5)
            
            data, outlier_stats = self.remove_outliers(
                data,
                columns=outlier_columns,
                method=outlier_method,
                threshold=outlier_threshold
            )
            report["steps"].append({
                "step": "remove_outliers",
                "method": outlier_method,
                "threshold": outlier_threshold,
                "stats": outlier_stats,
                "remaining": len(data)
            })
        
        # Statistiques finales
        report["final_count"] = len(data)
        report["total_removed"] = original_count - len(data)
        report["removal_percentage"] = round(
            (original_count - len(data)) / original_count * 100, 2
        ) if original_count > 0 else 0
        
        # Calculer les statistiques descriptives
        numeric_columns = [
            "temperature", "humidity", "TVOC", "CO2", 
            "PM1.0", "PM2.5", "PM10", "sound_level"
        ]
        report["statistics"] = self.get_statistics(data, numeric_columns)
        
        # Sauvegarder les données nettoyées
        cleaned_filename = f"cleaned_{filename}"
        output_path = self.save_cleaned_data(data, cleaned_filename)
        report["output_file"] = output_path
        report["cleaned_data"] = data
        
        return report
    
    def clean_all_datasets(self, config: dict | None = None) -> list[dict]:
        """
        Nettoie tous les fichiers JSON du dossier data.
        
        Args:
            config: Configuration du nettoyage
            
        Returns:
            Liste des rapports de nettoyage
        """
        reports = []
        
        for filepath in self.data_dir.glob("*.json"):
            # Ignorer les fichiers dans le dossier cleaned
            if "cleaned" in str(filepath):
                continue
            
            try:
                report = self.clean_dataset(filepath.name, config)
                # Ne pas inclure cleaned_data dans le rapport global
                report_summary = {k: v for k, v in report.items() if k != "cleaned_data"}
                reports.append(report_summary)
            except Exception as e:
                reports.append({
                    "filename": filepath.name,
                    "error": str(e)
                })
        
        return reports


# Instance singleton
data_cleaning_service = DataCleaningService()
