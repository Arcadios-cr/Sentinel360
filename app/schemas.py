from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class EvaluateRequest(BaseModel):
    """Requête d'évaluation d'un modèle."""
    y_true: List[float] = Field(..., description="Valeurs réelles observées")
    y_pred: List[float] = Field(..., description="Valeurs prédites par le modèle")
    baseline_rmse: Optional[float] = Field(None, description="RMSE de référence pour la détection de drift")


class DataDriftRequest(BaseModel):
    """Requête d'analyse de dérive des données."""
    reference: Dict[str, List[float]] = Field(..., description="Données de référence par feature")
    current: Dict[str, List[float]] = Field(..., description="Données actuelles par feature")
    alpha: float = Field(0.05, ge=0.001, le=0.5, description="Seuil de significativité statistique")


class ScheduleRequest(BaseModel):
    """
    Requête de création d'une tâche planifiée (F2-UC3).
    
    Permet de programmer des évaluations automatiques à intervalles réguliers.
    """
    model_id: str = Field(..., description="Identifiant du modèle à évaluer")
    interval_minutes: int = Field(
        ..., 
        ge=1, 
        le=10080,  # Max 1 semaine
        description="Intervalle entre chaque évaluation (en minutes)"
    )
    y_true: List[float] = Field(..., description="Valeurs réelles pour l'évaluation")
    y_pred: List[float] = Field(..., description="Valeurs prédites pour l'évaluation")
    baseline_rmse: Optional[float] = Field(None, description="RMSE de référence")
    max_runs: Optional[int] = Field(
        None, 
        ge=1, 
        description="Nombre maximum d'exécutions (None = infini)"
    )


# ============================================================
# Schémas pour F1-UC2 : Préparation et nettoyage des données
# ============================================================

class DataCleaningConfig(BaseModel):
    """Configuration pour le nettoyage des données."""
    remove_duplicates: bool = Field(True, description="Supprimer les doublons")
    duplicate_keys: Optional[List[str]] = Field(
        ["timestamp", "ID"],
        description="Colonnes pour identifier les doublons"
    )
    missing_strategy: str = Field(
        "fill",
        description="Stratégie pour les valeurs manquantes: 'remove' ou 'fill'"
    )
    missing_columns: Optional[List[str]] = Field(
        None,
        description="Colonnes à vérifier pour les valeurs manquantes"
    )
    numeric_strategy: str = Field(
        "median",
        description="Stratégie pour remplir les numériques: 'mean', 'median', 'zero'"
    )
    validate_ranges: bool = Field(True, description="Valider les plages de valeurs")
    validation_rules: Optional[Dict[str, tuple]] = Field(
        None,
        description="Règles de validation: {'colonne': (min, max)}"
    )
    remove_outliers: bool = Field(False, description="Supprimer les outliers")
    outlier_columns: Optional[List[str]] = Field(
        None,
        description="Colonnes pour la détection d'outliers"
    )
    outlier_method: str = Field("iqr", description="Méthode: 'iqr' ou 'zscore'")
    outlier_threshold: float = Field(1.5, description="Seuil de détection")


class DataCleaningRequest(BaseModel):
    """Requête de nettoyage d'un fichier de données."""
    filename: str = Field(..., description="Nom du fichier à nettoyer")
    config: Optional[DataCleaningConfig] = Field(
        None,
        description="Configuration de nettoyage (utilise les valeurs par défaut si None)"
    )


class CleaningStepResult(BaseModel):
    """Résultat d'une étape de nettoyage."""
    step: str = Field(..., description="Nom de l'étape")
    remaining: Optional[int] = Field(None, description="Nombre d'enregistrements restants")
    stats: Optional[Dict[str, Any]] = Field(None, description="Statistiques de l'étape")


class ColumnStatistics(BaseModel):
    """Statistiques d'une colonne numérique."""
    count: int = Field(..., description="Nombre de valeurs")
    missing: int = Field(..., description="Nombre de valeurs manquantes")
    min: float = Field(..., description="Valeur minimale")
    max: float = Field(..., description="Valeur maximale")
    mean: float = Field(..., description="Moyenne")
    median: float = Field(..., description="Médiane")
    std: float = Field(..., description="Écart-type")


class DataCleaningResponse(BaseModel):
    """Réponse du nettoyage de données."""
    filename: str = Field(..., description="Nom du fichier traité")
    original_count: int = Field(..., description="Nombre d'enregistrements originaux")
    final_count: int = Field(..., description="Nombre d'enregistrements après nettoyage")
    total_removed: int = Field(..., description="Total d'enregistrements supprimés")
    removal_percentage: float = Field(..., description="Pourcentage de données supprimées")
    timestamp: str = Field(..., description="Date/heure du traitement")
    steps: List[Dict[str, Any]] = Field(..., description="Détail des étapes de nettoyage")
    statistics: Dict[str, ColumnStatistics] = Field(
        ...,
        description="Statistiques descriptives par colonne"
    )
    output_file: str = Field(..., description="Chemin du fichier nettoyé")


class DataPreviewRequest(BaseModel):
    """Requête de prévisualisation des données."""
    filename: str = Field(..., description="Nom du fichier à prévisualiser")
    limit: int = Field(10, ge=1, le=100, description="Nombre d'enregistrements à afficher")


class DataPreviewResponse(BaseModel):
    """Réponse de prévisualisation des données."""
    filename: str = Field(..., description="Nom du fichier")
    total_records: int = Field(..., description="Nombre total d'enregistrements")
    preview: List[Dict[str, Any]] = Field(..., description="Aperçu des données")
    columns: List[str] = Field(..., description="Liste des colonnes")
    statistics: Dict[str, ColumnStatistics] = Field(
        ...,
        description="Statistiques descriptives"
    )


class DataFilesResponse(BaseModel):
    """Liste des fichiers de données disponibles."""
    files: List[str] = Field(..., description="Liste des fichiers JSON disponibles")
    cleaned_files: List[str] = Field(..., description="Liste des fichiers nettoyés")
    total_count: int = Field(..., description="Nombre total de fichiers")