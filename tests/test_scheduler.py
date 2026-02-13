"""
F2-UC3 : Tests pour la planification automatique des évaluations.

Ce module teste :
- Création de schedules
- Pause/Resume/Delete de schedules
- Exécution manuelle (trigger)
- Statistiques du scheduler
"""

import pytest
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from app.services.scheduler import Scheduler, ScheduleStatus, ScheduleConfig


@pytest.fixture
def fresh_scheduler():
    """Crée un scheduler vierge pour chaque test."""
    scheduler = Scheduler()
    # Vider les schedules existants
    scheduler._schedules.clear()
    scheduler._tasks.clear()
    
    # Callback de test simple
    def mock_evaluate(model_id, y_true, y_pred, baseline_rmse=None):
        return {
            "model_id": model_id,
            "score": 85.0,
            "metrics": {"rmse": 0.15}
        }
    
    scheduler.set_evaluation_callback(mock_evaluate)
    return scheduler


class TestScheduleCreation:
    """Tests de création de schedules."""

    def test_create_schedule_basic(self, fresh_scheduler):
        """Test de création d'un schedule basique."""
        schedule = fresh_scheduler.create_schedule(
            model_id="test_model",
            interval_minutes=60,
            y_true=[1.0, 2.0, 3.0],
            y_pred=[1.1, 2.1, 3.1],
            baseline_rmse=0.5
        )
        
        assert schedule.model_id == "test_model"
        assert schedule.interval_minutes == 60
        assert schedule.status == ScheduleStatus.ACTIVE
        assert schedule.run_count == 0
        assert schedule.baseline_rmse == 0.5

    def test_create_schedule_generates_unique_id(self, fresh_scheduler):
        """Test que chaque schedule a un ID unique."""
        schedule1 = fresh_scheduler.create_schedule(
            model_id="model_A",
            interval_minutes=30,
            y_true=[1.0],
            y_pred=[1.0]
        )
        
        schedule2 = fresh_scheduler.create_schedule(
            model_id="model_A",
            interval_minutes=30,
            y_true=[1.0],
            y_pred=[1.0]
        )
        
        assert schedule1.schedule_id != schedule2.schedule_id

    def test_create_schedule_with_max_runs(self, fresh_scheduler):
        """Test de création avec un nombre max d'exécutions."""
        schedule = fresh_scheduler.create_schedule(
            model_id="test_model",
            interval_minutes=5,
            y_true=[1.0, 2.0],
            y_pred=[1.0, 2.0],
            max_runs=10
        )
        
        assert schedule.max_runs == 10

    def test_create_schedule_sets_timestamps(self, fresh_scheduler):
        """Test que les timestamps sont correctement initialisés."""
        schedule = fresh_scheduler.create_schedule(
            model_id="test_model",
            interval_minutes=60,
            y_true=[1.0],
            y_pred=[1.0]
        )
        
        assert schedule.created_at is not None
        assert schedule.next_run is not None
        assert schedule.last_run is None  # Pas encore exécuté


class TestScheduleManagement:
    """Tests de gestion des schedules."""

    def test_list_schedules_empty(self, fresh_scheduler):
        """Test liste vide."""
        schedules = fresh_scheduler.list_schedules()
        assert schedules == []

    def test_list_schedules_with_filter(self, fresh_scheduler):
        """Test liste avec filtre par model_id."""
        fresh_scheduler.create_schedule(
            model_id="model_A",
            interval_minutes=60,
            y_true=[1.0],
            y_pred=[1.0]
        )
        fresh_scheduler.create_schedule(
            model_id="model_B",
            interval_minutes=30,
            y_true=[1.0],
            y_pred=[1.0]
        )
        
        all_schedules = fresh_scheduler.list_schedules()
        model_a_schedules = fresh_scheduler.list_schedules(model_id="model_A")
        
        assert len(all_schedules) == 2
        assert len(model_a_schedules) == 1
        assert model_a_schedules[0]["model_id"] == "model_A"

    def test_get_schedule_existing(self, fresh_scheduler):
        """Test récupération d'un schedule existant."""
        created = fresh_scheduler.create_schedule(
            model_id="test_model",
            interval_minutes=60,
            y_true=[1.0],
            y_pred=[1.0]
        )
        
        retrieved = fresh_scheduler.get_schedule(created.schedule_id)
        
        assert retrieved is not None
        assert retrieved.schedule_id == created.schedule_id

    def test_get_schedule_nonexistent(self, fresh_scheduler):
        """Test récupération d'un schedule inexistant."""
        result = fresh_scheduler.get_schedule("nonexistent_id")
        assert result is None

    def test_delete_schedule(self, fresh_scheduler):
        """Test suppression d'un schedule."""
        schedule = fresh_scheduler.create_schedule(
            model_id="test_model",
            interval_minutes=60,
            y_true=[1.0],
            y_pred=[1.0]
        )
        
        success = fresh_scheduler.delete_schedule(schedule.schedule_id)
        
        assert success is True
        assert fresh_scheduler.get_schedule(schedule.schedule_id) is None

    def test_delete_schedule_nonexistent(self, fresh_scheduler):
        """Test suppression d'un schedule inexistant."""
        success = fresh_scheduler.delete_schedule("nonexistent_id")
        assert success is False


class TestSchedulePauseResume:
    """Tests de pause et reprise des schedules."""

    def test_pause_schedule(self, fresh_scheduler):
        """Test mise en pause d'un schedule."""
        schedule = fresh_scheduler.create_schedule(
            model_id="test_model",
            interval_minutes=60,
            y_true=[1.0],
            y_pred=[1.0]
        )
        
        success = fresh_scheduler.pause_schedule(schedule.schedule_id)
        
        assert success is True
        updated = fresh_scheduler.get_schedule(schedule.schedule_id)
        assert updated.status == ScheduleStatus.PAUSED

    def test_resume_schedule(self, fresh_scheduler):
        """Test reprise d'un schedule en pause."""
        schedule = fresh_scheduler.create_schedule(
            model_id="test_model",
            interval_minutes=60,
            y_true=[1.0],
            y_pred=[1.0]
        )
        fresh_scheduler.pause_schedule(schedule.schedule_id)
        
        success = fresh_scheduler.resume_schedule(schedule.schedule_id)
        
        assert success is True
        updated = fresh_scheduler.get_schedule(schedule.schedule_id)
        assert updated.status == ScheduleStatus.ACTIVE

    def test_resume_active_schedule_fails(self, fresh_scheduler):
        """Test qu'on ne peut pas reprendre un schedule déjà actif."""
        schedule = fresh_scheduler.create_schedule(
            model_id="test_model",
            interval_minutes=60,
            y_true=[1.0],
            y_pred=[1.0]
        )
        
        # Le schedule est déjà actif
        success = fresh_scheduler.resume_schedule(schedule.schedule_id)
        assert success is False


class TestScheduleTrigger:
    """Tests du déclenchement manuel."""

    def test_trigger_now(self, fresh_scheduler):
        """Test déclenchement immédiat d'une évaluation."""
        schedule = fresh_scheduler.create_schedule(
            model_id="test_trigger",
            interval_minutes=60,
            y_true=[1.0, 2.0, 3.0],
            y_pred=[1.1, 2.1, 3.1]
        )
        
        result = fresh_scheduler.trigger_now(schedule.schedule_id)
        
        assert result is not None
        assert result["score"] == 85.0  # Valeur du mock
        
        # Vérifier que run_count a été incrémenté
        updated = fresh_scheduler.get_schedule(schedule.schedule_id)
        assert updated.run_count == 1
        assert updated.last_run is not None

    def test_trigger_nonexistent(self, fresh_scheduler):
        """Test trigger sur un schedule inexistant."""
        result = fresh_scheduler.trigger_now("nonexistent_id")
        assert result is None

    def test_trigger_updates_next_run(self, fresh_scheduler):
        """Test que trigger met à jour next_run."""
        schedule = fresh_scheduler.create_schedule(
            model_id="test_model",
            interval_minutes=60,
            y_true=[1.0],
            y_pred=[1.0]
        )
        
        initial_next_run = schedule.next_run
        fresh_scheduler.trigger_now(schedule.schedule_id)
        
        updated = fresh_scheduler.get_schedule(schedule.schedule_id)
        assert updated.next_run != initial_next_run


class TestSchedulerStats:
    """Tests des statistiques du scheduler."""

    def test_stats_empty(self, fresh_scheduler):
        """Test stats avec aucun schedule."""
        stats = fresh_scheduler.get_stats()
        
        assert stats["total_schedules"] == 0
        assert stats["active_tasks"] == 0

    def test_stats_with_schedules(self, fresh_scheduler):
        """Test stats avec des schedules."""
        fresh_scheduler.create_schedule(
            model_id="model_1",
            interval_minutes=60,
            y_true=[1.0],
            y_pred=[1.0]
        )
        schedule2 = fresh_scheduler.create_schedule(
            model_id="model_2",
            interval_minutes=30,
            y_true=[1.0],
            y_pred=[1.0]
        )
        fresh_scheduler.pause_schedule(schedule2.schedule_id)
        
        stats = fresh_scheduler.get_stats()
        
        assert stats["total_schedules"] == 2
        assert stats["status_counts"]["active"] == 1
        assert stats["status_counts"]["paused"] == 1


class TestMaxRuns:
    """Tests du comportement avec max_runs."""

    def test_schedule_completes_after_max_runs(self, fresh_scheduler):
        """Test que le schedule se termine après max_runs."""
        schedule = fresh_scheduler.create_schedule(
            model_id="test_model",
            interval_minutes=60,
            y_true=[1.0],
            y_pred=[1.0],
            max_runs=2
        )
        
        # Premier trigger
        fresh_scheduler.trigger_now(schedule.schedule_id)
        updated = fresh_scheduler.get_schedule(schedule.schedule_id)
        assert updated.status == ScheduleStatus.ACTIVE
        assert updated.run_count == 1
        
        # Deuxième trigger (atteint max_runs)
        fresh_scheduler.trigger_now(schedule.schedule_id)
        updated = fresh_scheduler.get_schedule(schedule.schedule_id)
        assert updated.status == ScheduleStatus.COMPLETED
        assert updated.run_count == 2
