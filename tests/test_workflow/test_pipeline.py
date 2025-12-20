"""Tests for Pipeline API."""

from unittest.mock import MagicMock

import pytest

from hpc_runner.workflow import DependencyType, Pipeline, PipelineJob


class TestPipeline:
    """Tests for Pipeline class."""

    def test_create_pipeline(self):
        """Test creating a pipeline."""
        p = Pipeline("my_pipeline")
        assert p.name == "my_pipeline"
        assert len(p) == 0

    def test_add_job(self):
        """Test adding a job to pipeline."""
        p = Pipeline()
        job = p.add("echo hello", name="step1")

        assert len(p) == 1
        assert job.name == "step1"
        assert job.job.command == "echo hello"

    def test_add_job_auto_name(self):
        """Test auto-generated job name."""
        p = Pipeline()
        job = p.add("echo hello")

        assert job.name == "step_1"

    def test_add_job_with_kwargs(self):
        """Test adding job with extra kwargs."""
        p = Pipeline()
        job = p.add("echo hello", name="step1", cpu=4, mem="8G")

        assert job.job.cpu == 4
        assert job.job.mem == "8G"

    def test_add_job_with_dependencies(self):
        """Test adding job with dependencies."""
        p = Pipeline()
        step1 = p.add("echo step1", name="step1")
        step2 = p.add("echo step2", name="step2", depends_on=["step1"])

        assert len(step2.depends_on) == 1
        assert step2.depends_on[0] is step1

    def test_add_job_with_pipeline_job_dependency(self):
        """Test adding job with PipelineJob dependency."""
        p = Pipeline()
        step1 = p.add("echo step1", name="step1")
        step2 = p.add("echo step2", name="step2", depends_on=[step1])

        assert step2.depends_on[0] is step1

    def test_duplicate_name_raises(self):
        """Test that duplicate job names raise error."""
        p = Pipeline()
        p.add("echo hello", name="step1")

        with pytest.raises(ValueError, match="already exists"):
            p.add("echo world", name="step1")

    def test_unknown_dependency_raises(self):
        """Test that unknown dependency raises error."""
        p = Pipeline()
        p.add("echo hello", name="step1")

        with pytest.raises(ValueError, match="Unknown dependency"):
            p.add("echo world", name="step2", depends_on=["nonexistent"])

    def test_topological_sort(self):
        """Test topological sorting of jobs."""
        p = Pipeline()
        step3 = p.add("echo step3", name="step3", depends_on=[])
        step1 = p.add("echo step1", name="step1", depends_on=[])
        step2 = p.add("echo step2", name="step2", depends_on=["step1", "step3"])

        sorted_jobs = p._topological_sort()

        # step1 and step3 should come before step2
        step2_idx = next(i for i, j in enumerate(sorted_jobs) if j.name == "step2")
        step1_idx = next(i for i, j in enumerate(sorted_jobs) if j.name == "step1")
        step3_idx = next(i for i, j in enumerate(sorted_jobs) if j.name == "step3")

        assert step1_idx < step2_idx
        assert step3_idx < step2_idx

    def test_circular_dependency_raises(self):
        """Test that circular dependencies raise error."""
        p = Pipeline()

        # Create jobs first without dependencies
        p.add("echo step1", name="step1")
        p.add("echo step2", name="step2", depends_on=["step1"])

        # Manually create a cycle
        p._name_map["step1"].depends_on.append(p._name_map["step2"])

        with pytest.raises(ValueError, match="Circular dependency"):
            p._topological_sort()

    def test_get_job(self):
        """Test getting job by name."""
        p = Pipeline()
        step1 = p.add("echo hello", name="step1")

        assert p.get_job("step1") is step1
        assert p.get_job("nonexistent") is None

    def test_context_manager(self):
        """Test pipeline as context manager."""
        with Pipeline("test") as p:
            p.add("echo hello", name="step1")

        assert len(p) == 1

    def test_iteration(self):
        """Test iterating over pipeline jobs."""
        p = Pipeline()
        p.add("echo step1", name="step1")
        p.add("echo step2", name="step2")

        names = [job.name for job in p]
        assert "step1" in names
        assert "step2" in names

    def test_submit_sets_dependencies(self):
        """Test that submit sets job dependencies correctly."""
        p = Pipeline()
        step1 = p.add("echo step1", name="step1")
        step2 = p.add("echo step2", name="step2", depends_on=["step1"])

        # Create mock scheduler
        mock_scheduler = MagicMock()
        mock_result1 = MagicMock()
        mock_result1.job_id = "123"
        mock_result2 = MagicMock()
        mock_result2.job_id = "456"

        mock_scheduler.submit.side_effect = [mock_result1, mock_result2]

        results = p.submit(scheduler=mock_scheduler)

        # Check that step2's job has step1's result as dependency
        calls = mock_scheduler.submit.call_args_list
        assert len(calls) == 2

        # The second job should have dependencies set
        second_job = calls[1][0][0]
        assert len(second_job.dependencies) == 1
        assert second_job.dependencies[0].job_id == "123"


class TestDependencyType:
    """Tests for DependencyType enum."""

    def test_dependency_types(self):
        """Test dependency type values."""
        assert str(DependencyType.AFTEROK) == "afterok"
        assert str(DependencyType.AFTERANY) == "afterany"
        assert str(DependencyType.AFTER) == "after"
        assert str(DependencyType.AFTERNOTOK) == "afternotok"
