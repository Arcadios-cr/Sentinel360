"""
F2-UC3 : Service de planification automatique des évaluations.

Ce module gère :
- La création de tâches planifiées pour évaluer les modèles
- L'exécution périodique en background (asyncio)
- Le stockage et la gestion des schedules
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScheduleStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ScheduleConfig:
    """Configuration d'une tâche planifiée."""
    schedule_id: str
    model_id: str
    interval_minutes: int
    y_true: List[float]
    y_pred: List[float]
    baseline_rmse: Optional[float] = None
    status: ScheduleStatus = ScheduleStatus.ACTIVE
    created_at: str = ""
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0
    max_runs: Optional[int] = None  # None = infini
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        if not self.next_run:
            self.next_run = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class Scheduler:
    """
    Gestionnaire de tâches planifiées pour les évaluations de modèles.
    Utilise asyncio pour l'exécution en background.
    """
    
    def __init__(self):
        self._schedules: Dict[str, ScheduleConfig] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._evaluation_callback: Optional[Callable] = None
        self._running = False
        self._load_schedules()
    
    def _schedules_file(self) -> Path:
        """Chemin du fichier de persistance des schedules."""
        data_dir = Path(__file__).resolve().parents[1] / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "schedules.json"
    
    def _load_schedules(self):
        """Charge les schedules depuis le fichier."""
        path = self._schedules_file()
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        item["status"] = ScheduleStatus(item["status"])
                        self._schedules[item["schedule_id"]] = ScheduleConfig(**item)
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Erreur chargement schedules: {e}")
    
    def _save_schedules(self):
        """Sauvegarde les schedules dans le fichier."""
        path = self._schedules_file()
        data = []
        for schedule in self._schedules.values():
            d = asdict(schedule)
            d["status"] = schedule.status.value
            data.append(d)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def set_evaluation_callback(self, callback: Callable):
        """Définit la fonction à appeler pour évaluer un modèle."""
        self._evaluation_callback = callback
    
    def create_schedule(
        self,
        model_id: str,
        interval_minutes: int,
        y_true: List[float],
        y_pred: List[float],
        baseline_rmse: Optional[float] = None,
        max_runs: Optional[int] = None
    ) -> ScheduleConfig:
        """
        Crée une nouvelle tâche planifiée.
        
        Args:
            model_id: Identifiant du modèle à évaluer
            interval_minutes: Intervalle entre chaque évaluation
            y_true: Valeurs réelles pour l'évaluation
            y_pred: Valeurs prédites pour l'évaluation
            baseline_rmse: RMSE de référence (optionnel)
            max_runs: Nombre max d'exécutions (None = infini)
        
        Returns:
            Configuration du schedule créé
        """
        schedule_id = f"sched_{model_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        schedule = ScheduleConfig(
            schedule_id=schedule_id,
            model_id=model_id,
            interval_minutes=interval_minutes,
            y_true=y_true,
            y_pred=y_pred,
            baseline_rmse=baseline_rmse,
            max_runs=max_runs
        )
        
        self._schedules[schedule_id] = schedule
        self._save_schedules()
        
        # Démarrer la tâche si le scheduler est actif
        if self._running:
            self._start_task(schedule_id)
        
        logger.info(f"Schedule créé: {schedule_id} pour modèle {model_id}")
        return schedule
    
    def get_schedule(self, schedule_id: str) -> Optional[ScheduleConfig]:
        """Récupère un schedule par son ID."""
        return self._schedules.get(schedule_id)
    
    def list_schedules(self, model_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Liste tous les schedules, optionnellement filtrés par modèle."""
        schedules = []
        for schedule in self._schedules.values():
            if model_id is None or schedule.model_id == model_id:
                d = asdict(schedule)
                d["status"] = schedule.status.value
                schedules.append(d)
        return schedules
    
    def pause_schedule(self, schedule_id: str) -> bool:
        """Met en pause un schedule."""
        if schedule_id not in self._schedules:
            return False
        
        self._schedules[schedule_id].status = ScheduleStatus.PAUSED
        self._save_schedules()
        
        # Annuler la tâche asyncio
        if schedule_id in self._tasks:
            self._tasks[schedule_id].cancel()
            del self._tasks[schedule_id]
        
        logger.info(f"Schedule pausé: {schedule_id}")
        return True
    
    def resume_schedule(self, schedule_id: str) -> bool:
        """Reprend un schedule en pause."""
        if schedule_id not in self._schedules:
            return False
        
        schedule = self._schedules[schedule_id]
        if schedule.status != ScheduleStatus.PAUSED:
            return False
        
        schedule.status = ScheduleStatus.ACTIVE
        schedule.next_run = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self._save_schedules()
        
        if self._running:
            self._start_task(schedule_id)
        
        logger.info(f"Schedule repris: {schedule_id}")
        return True
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """Supprime un schedule."""
        if schedule_id not in self._schedules:
            return False
        
        # Annuler la tâche
        if schedule_id in self._tasks:
            self._tasks[schedule_id].cancel()
            del self._tasks[schedule_id]
        
        del self._schedules[schedule_id]
        self._save_schedules()
        
        logger.info(f"Schedule supprimé: {schedule_id}")
        return True
    
    def trigger_now(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Déclenche immédiatement une évaluation pour un schedule."""
        if schedule_id not in self._schedules:
            return None
        
        schedule = self._schedules[schedule_id]
        return self._execute_evaluation(schedule)
    
    def _execute_evaluation(self, schedule: ScheduleConfig) -> Optional[Dict[str, Any]]:
        """Exécute une évaluation pour un schedule donné."""
        if not self._evaluation_callback:
            logger.error("Pas de callback d'évaluation défini")
            return None
        
        try:
            result = self._evaluation_callback(
                model_id=schedule.model_id,
                y_true=schedule.y_true,
                y_pred=schedule.y_pred,
                baseline_rmse=schedule.baseline_rmse
            )
            
            # Mettre à jour le schedule
            now = datetime.now(timezone.utc)
            schedule.last_run = now.isoformat().replace("+00:00", "Z")
            schedule.run_count += 1
            
            # Calculer le prochain run
            next_run = now + timedelta(minutes=schedule.interval_minutes)
            schedule.next_run = next_run.isoformat().replace("+00:00", "Z")
            
            # Vérifier si max_runs atteint
            if schedule.max_runs and schedule.run_count >= schedule.max_runs:
                schedule.status = ScheduleStatus.COMPLETED
                logger.info(f"Schedule {schedule.schedule_id} terminé (max_runs atteint)")
            
            self._save_schedules()
            
            logger.info(f"Évaluation exécutée pour {schedule.model_id} (run #{schedule.run_count})")
            return result
            
        except Exception as e:
            logger.error(f"Erreur évaluation {schedule.schedule_id}: {e}")
            schedule.status = ScheduleStatus.ERROR
            self._save_schedules()
            return None
    
    async def _run_schedule_loop(self, schedule_id: str):
        """Boucle asyncio pour un schedule donné."""
        while True:
            schedule = self._schedules.get(schedule_id)
            if not schedule or schedule.status != ScheduleStatus.ACTIVE:
                break
            
            # Attendre jusqu'au prochain run
            if schedule.next_run:
                next_run_dt = datetime.fromisoformat(
                    schedule.next_run.replace("Z", "+00:00")
                )
                now = datetime.now(timezone.utc)
                wait_seconds = (next_run_dt - now).total_seconds()
                
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)
            
            # Vérifier que le schedule est toujours actif
            schedule = self._schedules.get(schedule_id)
            if not schedule or schedule.status != ScheduleStatus.ACTIVE:
                break
            
            # Exécuter l'évaluation
            self._execute_evaluation(schedule)
            
            # Vérifier si terminé
            if schedule.status != ScheduleStatus.ACTIVE:
                break
    
    def _start_task(self, schedule_id: str):
        """Démarre une tâche asyncio pour un schedule."""
        if schedule_id in self._tasks:
            return
        
        schedule = self._schedules.get(schedule_id)
        if not schedule or schedule.status != ScheduleStatus.ACTIVE:
            return
        
        try:
            # Essayer d'obtenir la boucle d'événements en cours
            loop = asyncio.get_running_loop()
            task = loop.create_task(self._run_schedule_loop(schedule_id))
            self._tasks[schedule_id] = task
        except RuntimeError:
            # Pas de boucle en cours (appelé depuis un contexte sync)
            # La tâche sera démarrée au prochain appel de start() ou via trigger
            logger.debug(f"Pas de boucle asyncio active, schedule {schedule_id} sera démarré plus tard")
    
    async def start(self):
        """Démarre le scheduler et toutes les tâches actives."""
        self._running = True
        self._loop = asyncio.get_running_loop()
        logger.info("Scheduler démarré")
        
        # Démarrer toutes les tâches actives
        for schedule_id, schedule in self._schedules.items():
            if schedule.status == ScheduleStatus.ACTIVE:
                self._start_task(schedule_id)
    
    async def stop(self):
        """Arrête le scheduler et toutes les tâches."""
        self._running = False
        
        # Annuler toutes les tâches
        for task in self._tasks.values():
            task.cancel()
        
        self._tasks.clear()
        logger.info("Scheduler arrêté")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du scheduler."""
        status_counts = {s.value: 0 for s in ScheduleStatus}
        for schedule in self._schedules.values():
            status_counts[schedule.status.value] += 1
        
        return {
            "running": self._running,
            "total_schedules": len(self._schedules),
            "active_tasks": len(self._tasks),
            "status_counts": status_counts
        }


# Instance globale du scheduler
scheduler = Scheduler()
