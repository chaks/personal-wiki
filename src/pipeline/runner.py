# src/pipeline/runner.py
"""Pipeline execution engine."""
import logging
from typing import Sequence

from src.pipeline.stages import PipelineStage, PipelineContext

logger = logging.getLogger(__name__)


class PipelineRunner:
    """Executes pipeline stages sequentially.

    The runner manages stage execution order, logging, and error propagation.
    Stages are executed in the order they were added.

    If a stage raises an exception, execution stops and the error is
    propagated to the caller. The error is also stored in the context.

    Example:
        runner = PipelineRunner()
        runner.add_stage(ConvertStage())
        runner.add_stage(ExtractStage())
        runner.add_stage(WriteStage())
        result = runner.run(initial_context)
    """

    def __init__(self):
        """Initialize the pipeline runner with an empty stage list."""
        self.stages: list[PipelineStage] = []

    def add_stage(self, stage: PipelineStage) -> "PipelineRunner":
        """Add a stage to the pipeline.

        Args:
            stage: The stage to add

        Returns:
            Self for method chaining
        """
        self.stages.append(stage)
        logger.debug(f"Added stage: {stage}")
        return self

    def run(self, context: PipelineContext) -> PipelineContext:
        """Execute all stages sequentially.

        Args:
            context: Initial pipeline context

        Returns:
            Final pipeline context after all stages complete

        Raises:
            Exception: Re-raises any exception from a failing stage
        """
        logger.info(f"Starting pipeline with {len(self.stages)} stage(s)")

        for i, stage in enumerate(self.stages):
            logger.debug(f"Executing stage {i + 1}/{len(self.stages)}: {stage}")

            try:
                context = stage.execute(context)
                logger.debug(f"Stage {stage} completed successfully")
            except Exception as e:
                logger.error(f"Stage {stage} failed: {e}")
                context.error = e
                raise

        logger.info("Pipeline completed successfully")
        return context
