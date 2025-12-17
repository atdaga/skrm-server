"""Business logic for deployment environment management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    DeploymentEnvAlreadyExistsException,
    DeploymentEnvNotFoundException,
    DeploymentEnvUpdateConflictException,
)
from ...models import KDeploymentEnv
from ...schemas.deployment_env import DeploymentEnvCreate, DeploymentEnvUpdate
from ..deps import verify_organization_membership


async def create_deployment_env(
    deployment_env_data: DeploymentEnvCreate,
    user_id: UUID,
    org_id: UUID,
    db: AsyncSession,
) -> KDeploymentEnv:
    """Create a new deployment environment.

    Args:
        deployment_env_data: Deployment environment creation data
        user_id: ID of the user creating the deployment environment
        org_id: Organization ID for the deployment environment
        db: Database session
    Returns:
        The created deployment environment model

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        DeploymentEnvAlreadyExistsException: If a deployment environment with the same name already exists in the organization
    """
    # Check if we're already in a transaction (e.g., from txs module)
    in_transaction = db.in_transaction()

    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    # Create new deployment environment with audit fields
    new_deployment_env = KDeploymentEnv(
        name=deployment_env_data.name,
        org_id=org_id,
        meta=deployment_env_data.meta,
        created_by=user_id,
        last_modified_by=user_id,
    )

    db.add(new_deployment_env)

    try:
        if in_transaction:  # pragma: no cover - tested via txs integration
            # Already in a transaction (managed by txs), just flush
            await db.flush()  # pragma: no cover
        else:
            # No active transaction, commit our changes
            await db.commit()
        await db.refresh(new_deployment_env)
    except IntegrityError as e:  # pragma: no cover
        if not in_transaction:  # pragma: no cover
            await db.rollback()  # pragma: no cover
        raise DeploymentEnvAlreadyExistsException(  # pragma: no cover
            name=deployment_env_data.name, scope=str(org_id)
        ) from e

    return new_deployment_env


async def list_deployment_envs(
    org_id: UUID, user_id: UUID, db: AsyncSession
) -> list[KDeploymentEnv]:
    """List all deployment environments in the given organization.

    Args:
        org_id: Organization ID to filter deployment environments by
        user_id: ID of the user making the request
        db: Database session

    Returns:
        List of deployment environment models

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KDeploymentEnv).where(KDeploymentEnv.org_id == org_id, KDeploymentEnv.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    deployment_envs = result.scalars().all()
    return list(deployment_envs)


async def get_deployment_env(
    deployment_env_id: UUID, org_id: UUID, user_id: UUID, db: AsyncSession
) -> KDeploymentEnv:
    """Get a single deployment environment by ID.

    Args:
        deployment_env_id: ID of the deployment environment to retrieve
        org_id: Organization ID to filter by
        user_id: ID of the user making the request
        db: Database session

    Returns:
        The deployment environment model

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        DeploymentEnvNotFoundException: If the deployment environment is not found in the given organization
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KDeploymentEnv).where(KDeploymentEnv.id == deployment_env_id, KDeploymentEnv.org_id == org_id, KDeploymentEnv.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    deployment_env = result.scalar_one_or_none()

    if not deployment_env:
        raise DeploymentEnvNotFoundException(
            deployment_env_id=deployment_env_id, scope=str(org_id)
        )

    return deployment_env


async def update_deployment_env(
    deployment_env_id: UUID,
    deployment_env_data: DeploymentEnvUpdate,
    user_id: UUID,
    org_id: UUID,
    db: AsyncSession,
) -> KDeploymentEnv:
    """Update a deployment environment.

    Args:
        deployment_env_id: ID of the deployment environment to update
        deployment_env_data: Deployment environment update data
        user_id: ID of the user performing the update
        org_id: Organization ID to filter by
        db: Database session
    Returns:
        The updated deployment environment model

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        DeploymentEnvNotFoundException: If the deployment environment is not found
        DeploymentEnvUpdateConflictException: If updating causes a name conflict
    """
    # Check if we're already in a transaction (e.g., from txs module)
    in_transaction = db.in_transaction()

    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KDeploymentEnv).where(KDeploymentEnv.id == deployment_env_id, KDeploymentEnv.org_id == org_id, KDeploymentEnv.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    deployment_env = result.scalar_one_or_none()

    if not deployment_env:
        raise DeploymentEnvNotFoundException(
            deployment_env_id=deployment_env_id, scope=str(org_id)
        )

    # Update only provided fields
    if deployment_env_data.name is not None:
        deployment_env.name = deployment_env_data.name
    if deployment_env_data.meta is not None:
        deployment_env.meta = deployment_env_data.meta

    # Update audit fields
    deployment_env.last_modified = datetime.now()
    deployment_env.last_modified_by = user_id

    try:
        if in_transaction:  # pragma: no cover - tested via txs integration
            # Already in a transaction (managed by txs), just flush
            await db.flush()  # pragma: no cover
        else:  # pragma: no cover - hard to test due to autobegin
            # No active transaction, commit our changes
            await db.commit()  # pragma: no cover
        await db.refresh(deployment_env)
    except IntegrityError as e:  # pragma: no cover
        if not in_transaction:  # pragma: no cover
            await db.rollback()  # pragma: no cover
        raise DeploymentEnvUpdateConflictException(  # pragma: no cover
            deployment_env_id=deployment_env_id,
            name=deployment_env_data.name or deployment_env.name,
            scope=str(org_id),
        ) from e

    return deployment_env


async def delete_deployment_env(
    deployment_env_id: UUID,
    org_id: UUID,
    user_id: UUID,
    db: AsyncSession,
    hard_delete: bool = False,
) -> None:
    """Delete a deployment environment.

    Args:
        deployment_env_id: ID of the deployment environment to delete
        org_id: Organization ID to filter by
        user_id: ID of the user making the request
        db: Database session
        hard_delete: If True, permanently delete the deployment environment. If False, soft delete.

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        DeploymentEnvNotFoundException: If the deployment environment is not found
    """
    # Check if we're already in a transaction (e.g., from txs module)
    in_transaction = db.in_transaction()

    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KDeploymentEnv).where(KDeploymentEnv.id == deployment_env_id, KDeploymentEnv.org_id == org_id, KDeploymentEnv.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    deployment_env = result.scalar_one_or_none()

    if not deployment_env:
        raise DeploymentEnvNotFoundException(
            deployment_env_id=deployment_env_id, scope=str(org_id)
        )

    if hard_delete:  # pragma: no cover
        await db.delete(deployment_env)  # pragma: no cover
    else:
        deployment_env.deleted_at = datetime.now()
        deployment_env.last_modified = datetime.now()
        deployment_env.last_modified_by = user_id
    if not in_transaction:  # pragma: no cover - hard to test due to autobegin
        # No active transaction, commit our changes
        await db.commit()  # pragma: no cover
