"""
Trigger System - Webhooks and polling triggers
"""

from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import uuid
import json
import logging
import aiohttp
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class TriggerType(str, Enum):
    WEBHOOK = "webhook"
    POLLING = "polling"
    SCHEDULED = "scheduled"
    STREAMING = "streaming"
    MANUAL = "manual"

class TriggerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PAUSED = "paused"

class WebhookConfig(BaseModel):
    """Configuration for webhook triggers"""
    endpoint: str
    method: str = "POST"
    headers: Dict[str, str] = {}
    secret: Optional[str] = None  # For signature verification
    retry_policy: Dict[str, Any] = {}

class PollingConfig(BaseModel):
    """Configuration for polling triggers"""
    interval: int  # seconds
    endpoint: Optional[str] = None
    method: str = "GET"
    headers: Dict[str, str] = {}
    params: Dict[str, Any] = {}
    last_poll: Optional[datetime] = None
    cursor: Optional[str] = None  # For pagination

class ScheduledConfig(BaseModel):
    """Configuration for scheduled triggers"""
    cron_expression: str
    timezone: str = "UTC"
    next_run: Optional[datetime] = None

class TriggerDefinition(BaseModel):
    """Definition of a trigger"""
    trigger_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    type: TriggerType
    connector_name: str
    connector_trigger: str
    config: Dict[str, Any] = {}
    filter_conditions: Dict[str, Any] = {}  # Event filtering
    transformation: Optional[str] = None  # Event transformation
    workflow_id: Optional[str] = None  # Associated workflow
    status: TriggerStatus = TriggerStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = {}

class TriggerEvent(BaseModel):
    """Trigger event data"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trigger_id: str
    trigger_type: TriggerType
    data: Dict[str, Any] = {}
    received_at: datetime = Field(default_factory=datetime.now)
    processed: bool = False
    workflow_id: Optional[str] = None
    metadata: Dict[str, Any] = {}

class WebhookHandler:
    """Handler for webhook triggers"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.webhooks: Dict[str, TriggerDefinition] = {}
        self.event_handlers: List[Callable] = []
    
    def register_webhook(self, trigger: TriggerDefinition) -> str:
        """Register a webhook trigger"""
        if trigger.type != TriggerType.WEBHOOK:
            raise ValueError("Trigger type must be webhook")
        
        self.webhooks[trigger.trigger_id] = trigger
        
        # Generate webhook endpoint URL
        webhook_url = f"{self.base_url}/webhooks/{trigger.trigger_id}"
        
        logger.info(f"Registered webhook: {trigger.name} at {webhook_url}")
        return webhook_url
    
    def add_event_handler(self, handler: Callable):
        """Add event handler for webhook events"""
        self.event_handlers.append(handler)
    
    async def handle_webhook(
        self,
        trigger_id: str,
        data: Dict[str, Any],
        headers: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Handle incoming webhook request"""
        trigger = self.webhooks.get(trigger_id)
        if not trigger:
            return {"error": "Webhook not found"}, 404
        
        if trigger.status != TriggerStatus.ACTIVE:
            return {"error": "Webhook not active"}, 400
        
        # Verify signature if secret is configured
        webhook_config = WebhookConfig(**trigger.config)
        if webhook_config.secret:
            if not self._verify_signature(data, headers, webhook_config.secret):
                return {"error": "Invalid signature"}, 401
        
        # Create event
        event = TriggerEvent(
            trigger_id=trigger_id,
            trigger_type=TriggerType.WEBHOOK,
            data=data,
            workflow_id=trigger.workflow_id
        )
        
        # Apply filters
        if not self._apply_filters(event, trigger.filter_conditions):
            return {"status": "filtered"}, 200
        
        # Apply transformation if configured
        if trigger.transformation:
            event.data = self._apply_transformation(event.data, trigger.transformation)
        
        # Notify handlers
        for handler in self.event_handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Event handler failed: {str(e)}")
        
        return {"status": "processed", "event_id": event.event_id}, 200
    
    def _verify_signature(
        self,
        data: Dict[str, Any],
        headers: Dict[str, str],
        secret: str
    ) -> bool:
        """Verify webhook signature"""
        # Simple HMAC verification - in production, use proper crypto
        import hmac
        import hashlib
        
        signature = headers.get("X-Signature", "")
        expected = hmac.new(
            secret.encode(),
            json.dumps(data, sort_keys=True).encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, f"sha256={expected}")
    
    def _apply_filters(self, event: TriggerEvent, filters: Dict[str, Any]) -> bool:
        """Apply filter conditions to event"""
        if not filters:
            return True
        
        # Simple filter evaluation - in production, use proper expression parser
        for key, condition in filters.items():
            if key not in event.data:
                return False
            
            value = event.data[key]
            
            if isinstance(condition, dict):
                # Range filter
                if "min" in condition and value < condition["min"]:
                    return False
                if "max" in condition and value > condition["max"]:
                    return False
            elif isinstance(condition, list):
                # Enum filter
                if value not in condition:
                    return False
            else:
                # Exact match
                if value != condition:
                    return False
        
        return True
    
    def _apply_transformation(self, data: Dict[str, Any], transformation: str) -> Dict[str, Any]:
        """Apply transformation to event data"""
        # Simple transformation using eval - in production, use proper expression engine
        try:
            # Create a safe context for evaluation
            context = {"data": data, "result": {}}
            exec(transformation, {}, context)
            return context.get("result", data)
        except Exception as e:
            logger.error(f"Transformation failed: {str(e)}")
            return data

class PollingManager:
    """Manager for polling triggers"""
    
    def __init__(self):
        self.polling_triggers: Dict[str, TriggerDefinition] = {}
        self.polling_tasks: Dict[str, asyncio.Task] = {}
        self.event_handlers: List[Callable] = []
        self._running = False
    
    def register_polling_trigger(self, trigger: TriggerDefinition):
        """Register a polling trigger"""
        if trigger.type != TriggerType.POLLING:
            raise ValueError("Trigger type must be polling")
        
        self.polling_triggers[trigger.trigger_id] = trigger
        
        # Start polling task if active
        if trigger.status == TriggerStatus.ACTIVE and self._running:
            self._start_polling(trigger.trigger_id)
        
        logger.info(f"Registered polling trigger: {trigger.name}")
    
    def add_event_handler(self, handler: Callable):
        """Add event handler for polling events"""
        self.event_handlers.append(handler)
    
    async def start(self):
        """Start all polling tasks"""
        self._running = True
        
        for trigger_id, trigger in self.polling_triggers.items():
            if trigger.status == TriggerStatus.ACTIVE:
                self._start_polling(trigger_id)
        
        logger.info("Polling manager started")
    
    async def stop(self):
        """Stop all polling tasks"""
        self._running = False
        
        for task in self.polling_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self.polling_tasks:
            await asyncio.gather(*self.polling_tasks.values(), return_exceptions=True)
        
        self.polling_tasks.clear()
        logger.info("Polling manager stopped")
    
    def _start_polling(self, trigger_id: str):
        """Start polling for a specific trigger"""
        if trigger_id in self.polling_tasks:
            return
        
        trigger = self.polling_triggers.get(trigger_id)
        if not trigger:
            return
        
        task = asyncio.create_task(self._poll_loop(trigger_id))
        self.polling_tasks[trigger_id] = task
    
    def _stop_polling(self, trigger_id: str):
        """Stop polling for a specific trigger"""
        if trigger_id in self.polling_tasks:
            self.polling_tasks[trigger_id].cancel()
            del self.polling_tasks[trigger_id]
    
    async def _poll_loop(self, trigger_id: str):
        """Main polling loop"""
        trigger = self.polling_triggers.get(trigger_id)
        if not trigger:
            return
        
        polling_config = PollingConfig(**trigger.config)
        
        while self._running and trigger.status == TriggerStatus.ACTIVE:
            try:
                # Poll for events
                events = await self._poll_events(trigger, polling_config)
                
                # Process events
                for event_data in events:
                    event = TriggerEvent(
                        trigger_id=trigger_id,
                        trigger_type=TriggerType.POLLING,
                        data=event_data,
                        workflow_id=trigger.workflow_id
                    )
                    
                    # Apply filters
                    if self._apply_filters(event, trigger.filter_conditions):
                        # Apply transformation
                        if trigger.transformation:
                            event.data = self._apply_transformation(
                                event.data, trigger.transformation
                            )
                        
                        # Notify handlers
                        for handler in self.event_handlers:
                            try:
                                await handler(event)
                            except Exception as e:
                                logger.error(f"Event handler failed: {str(e)}")
                
                # Wait for next poll
                await asyncio.sleep(polling_config.interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Polling loop error for {trigger_id}: {str(e)}")
                await asyncio.sleep(min(polling_config.interval, 60))  # Error backoff
    
    async def _poll_events(
        self,
        trigger: TriggerDefinition,
        config: PollingConfig
    ) -> List[Dict[str, Any]]:
        """Poll for events from external source"""
        try:
            # Make HTTP request
            async with aiohttp.ClientSession() as session:
                params = config.params.copy()
                
                # Add cursor for pagination if available
                if config.cursor:
                    params["cursor"] = config.cursor
                
                async with session.request(
                    config.method,
                    config.endpoint,
                    headers=config.headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract events and cursor
                        events = data.get("events", data)  # Handle different response formats
                        cursor = data.get("cursor")
                        
                        # Update cursor
                        if cursor:
                            config.cursor = cursor
                            trigger.config = config.dict()
                        
                        return events if isinstance(events, list) else [events]
                    else:
                        logger.error(f"Polling request failed: {response.status}")
                        return []
        
        except Exception as e:
            logger.error(f"Polling error: {str(e)}")
            return []
    
    def _apply_filters(self, event: TriggerEvent, filters: Dict[str, Any]) -> bool:
        """Apply filter conditions to event (same as webhook)"""
        if not filters:
            return True
        
        for key, condition in filters.items():
            if key not in event.data:
                return False
            
            value = event.data[key]
            
            if isinstance(condition, dict):
                if "min" in condition and value < condition["min"]:
                    return False
                if "max" in condition and value > condition["max"]:
                    return False
            elif isinstance(condition, list):
                if value not in condition:
                    return False
            else:
                if value != condition:
                    return False
        
        return True
    
    def _apply_transformation(self, data: Dict[str, Any], transformation: str) -> Dict[str, Any]:
        """Apply transformation to event data (same as webhook)"""
        try:
            context = {"data": data, "result": {}}
            exec(transformation, {}, context)
            return context.get("result", data)
        except Exception as e:
            logger.error(f"Transformation failed: {str(e)}")
            return data

class ScheduledManager:
    """Manager for scheduled triggers"""
    
    def __init__(self):
        self.scheduled_triggers: Dict[str, TriggerDefinition] = {}
        self.scheduled_tasks: Dict[str, asyncio.Task] = {}
        self.event_handlers: List[Callable] = []
        self._running = False
    
    def register_scheduled_trigger(self, trigger: TriggerDefinition):
        """Register a scheduled trigger"""
        if trigger.type != TriggerType.SCHEDULED:
            raise ValueError("Trigger type must be scheduled")
        
        self.scheduled_triggers[trigger.trigger_id] = trigger
        
        # Schedule task if active
        if trigger.status == TriggerStatus.ACTIVE and self._running:
            self._schedule_trigger(trigger.trigger_id)
        
        logger.info(f"Registered scheduled trigger: {trigger.name}")
    
    def add_event_handler(self, handler: Callable):
        """Add event handler for scheduled events"""
        self.event_handlers.append(handler)
    
    async def start(self):
        """Start the scheduled manager"""
        self._running = True
        
        for trigger_id, trigger in self.scheduled_triggers.items():
            if trigger.status == TriggerStatus.ACTIVE:
                self._schedule_trigger(trigger_id)
        
        logger.info("Scheduled manager started")
    
    async def stop(self):
        """Stop the scheduled manager"""
        self._running = False
        
        for task in self.scheduled_tasks.values():
            task.cancel()
        
        if self.scheduled_tasks:
            await asyncio.gather(*self.scheduled_tasks.values(), return_exceptions=True)
        
        self.scheduled_tasks.clear()
        logger.info("Scheduled manager stopped")
    
    def _schedule_trigger(self, trigger_id: str):
        """Schedule a specific trigger"""
        if trigger_id in self.scheduled_tasks:
            return
        
        trigger = self.scheduled_triggers.get(trigger_id)
        if not trigger:
            return
        
        task = asyncio.create_task(self._schedule_loop(trigger_id))
        self.scheduled_tasks[trigger_id] = task
    
    def _unschedule_trigger(self, trigger_id: str):
        """Unschedule a specific trigger"""
        if trigger_id in self.scheduled_tasks:
            self.scheduled_tasks[trigger_id].cancel()
            del self.scheduled_tasks[trigger_id]
    
    async def _schedule_loop(self, trigger_id: str):
        """Main scheduling loop"""
        trigger = self.scheduled_triggers.get(trigger_id)
        if not trigger:
            return
        
        scheduled_config = ScheduledConfig(**trigger.config)
        
        while self._running and trigger.status == TriggerStatus.ACTIVE:
            try:
                # Calculate next run time
                if not scheduled_config.next_run:
                    scheduled_config.next_run = self._calculate_next_run(scheduled_config)
                    trigger.config = scheduled_config.dict()
                
                # Wait until next run
                now = datetime.now()
                if scheduled_config.next_run > now:
                    sleep_time = (scheduled_config.next_run - now).total_seconds()
                    await asyncio.sleep(sleep_time)
                
                # Check if still active and time to run
                if (self._running and 
                    trigger.status == TriggerStatus.ACTIVE and
                    scheduled_config.next_run <= datetime.now()):
                    
                    # Create event
                    event = TriggerEvent(
                        trigger_id=trigger_id,
                        trigger_type=TriggerType.SCHEDULED,
                        data={"scheduled_time": scheduled_config.next_run.isoformat()},
                        workflow_id=trigger.workflow_id
                    )
                    
                    # Notify handlers
                    for handler in self.event_handlers:
                        try:
                            await handler(event)
                        except Exception as e:
                            logger.error(f"Event handler failed: {str(e)}")
                    
                    # Calculate next run
                    scheduled_config.next_run = self._calculate_next_run(scheduled_config)
                    trigger.config = scheduled_config.dict()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Schedule loop error for {trigger_id}: {str(e)}")
                await asyncio.sleep(60)  # Error backoff
    
    def _calculate_next_run(self, config: ScheduledConfig) -> datetime:
        """Calculate next run time from cron expression"""
        # Simple cron parsing - in production, use proper cron library
        try:
            from croniter import croniter
            cron = croniter(config.cron_expression, datetime.now())
            return cron.get_next(datetime)
        except ImportError:
            # Fallback to simple intervals
            return datetime.now() + timedelta(minutes=1)

class TriggerSystem:
    """Main trigger system combining all trigger types"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.webhook_handler = WebhookHandler(base_url)
        self.polling_manager = PollingManager()
        self.scheduled_manager = ScheduledManager()
        self.triggers: Dict[str, TriggerDefinition] = {}
        self.workflow_triggers: Dict[str, List[str]] = {}  # workflow_id -> trigger_ids
        self.event_handlers: List[Callable] = []
    
    async def start(self):
        """Start the trigger system"""
        await self.polling_manager.start()
        await self.scheduled_manager.start()
        
        # Add event handlers
        self.webhook_handler.add_event_handler(self._handle_event)
        self.polling_manager.add_event_handler(self._handle_event)
        self.scheduled_manager.add_event_handler(self._handle_event)
        
        logger.info("Trigger system started")
    
    async def stop(self):
        """Stop the trigger system"""
        await self.polling_manager.stop()
        await self.scheduled_manager.stop()
        logger.info("Trigger system stopped")
    
    def register_trigger(self, trigger: TriggerDefinition) -> str:
        """Register a trigger"""
        self.triggers[trigger.trigger_id] = trigger
        
        # Associate with workflow
        if trigger.workflow_id:
            if trigger.workflow_id not in self.workflow_triggers:
                self.workflow_triggers[trigger.workflow_id] = []
            self.workflow_triggers[trigger.workflow_id].append(trigger.trigger_id)
        
        # Register with appropriate manager
        if trigger.type == TriggerType.WEBHOOK:
            return self.webhook_handler.register_webhook(trigger)
        elif trigger.type == TriggerType.POLLING:
            self.polling_manager.register_polling_trigger(trigger)
        elif trigger.type == TriggerType.SCHEDULED:
            self.scheduled_manager.register_scheduled_trigger(trigger)
        
        return trigger.trigger_id
    
    def register_workflow_trigger(self, workflow_id: str, trigger_config: Dict[str, Any]):
        """Register a trigger for a workflow"""
        trigger = TriggerDefinition(
            name=f"Workflow {workflow_id} Trigger",
            type=TriggerType(trigger_config.get("type", "manual")),
            connector_name=trigger_config.get("connector_name", "system"),
            connector_trigger=trigger_config.get("connector_trigger", "workflow_start"),
            config=trigger_config.get("config", {}),
            workflow_id=workflow_id
        )
        
        return self.register_trigger(trigger)
    
    def get_trigger(self, trigger_id: str) -> Optional[TriggerDefinition]:
        """Get trigger by ID"""
        return self.triggers.get(trigger_id)
    
    def list_triggers(
        self,
        workflow_id: str = None,
        trigger_type: TriggerType = None
    ) -> List[TriggerDefinition]:
        """List triggers with optional filters"""
        triggers = list(self.triggers.values())
        
        if workflow_id:
            triggers = [t for t in triggers if t.workflow_id == workflow_id]
        
        if trigger_type:
            triggers = [t for t in triggers if t.type == trigger_type]
        
        return triggers
    
    def update_trigger_status(self, trigger_id: str, status: TriggerStatus):
        """Update trigger status"""
        trigger = self.triggers.get(trigger_id)
        if not trigger:
            return
        
        old_status = trigger.status
        trigger.status = status
        trigger.updated_at = datetime.now()
        
        # Update manager-specific status
        if trigger.type == TriggerType.POLLING:
            if status == TriggerStatus.ACTIVE and old_status != TriggerStatus.ACTIVE:
                self.polling_manager._start_polling(trigger_id)
            elif status != TriggerStatus.ACTIVE and old_status == TriggerStatus.ACTIVE:
                self.polling_manager._stop_polling(trigger_id)
        
        elif trigger.type == TriggerType.SCHEDULED:
            if status == TriggerStatus.ACTIVE and old_status != TriggerStatus.ACTIVE:
                self.scheduled_manager._schedule_trigger(trigger_id)
            elif status != TriggerStatus.ACTIVE and old_status == TriggerStatus.ACTIVE:
                self.scheduled_manager._unschedule_trigger(trigger_id)
    
    def remove_trigger(self, trigger_id: str) -> bool:
        """Remove a trigger"""
        trigger = self.triggers.get(trigger_id)
        if not trigger:
            return False
        
        # Remove from workflow association
        if trigger.workflow_id and trigger.workflow_id in self.workflow_triggers:
            self.workflow_triggers[trigger.workflow_id].remove(trigger_id)
        
        # Remove from appropriate manager
        if trigger.type == TriggerType.WEBHOOK:
            del self.webhook_handler.webhooks[trigger_id]
        elif trigger.type == TriggerType.POLLING:
            self.polling_manager._stop_polling(trigger_id)
            del self.polling_manager.polling_triggers[trigger_id]
        elif trigger.type == TriggerType.SCHEDULED:
            self.scheduled_manager._unschedule_trigger(trigger_id)
            del self.scheduled_manager.scheduled_triggers[trigger_id]
        
        del self.triggers[trigger_id]
        return True
    
    def add_event_handler(self, handler: Callable):
        """Add global event handler"""
        self.event_handlers.append(handler)
    
    async def _handle_event(self, event: TriggerEvent):
        """Handle trigger events"""
        # Notify global handlers
        for handler in self.event_handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Global event handler failed: {str(e)}")
    
    def get_webhook_url(self, trigger_id: str) -> Optional[str]:
        """Get webhook URL for a trigger"""
        trigger = self.triggers.get(trigger_id)
        if trigger and trigger.type == TriggerType.WEBHOOK:
            return f"{self.webhook_handler.base_url}/webhooks/{trigger_id}"
        return None
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        return {
            "total_triggers": len(self.triggers),
            "triggers_by_type": {
                trigger_type.value: len([t for t in self.triggers.values() if t.type == trigger_type])
                for trigger_type in TriggerType
            },
            "triggers_by_status": {
                status.value: len([t for t in self.triggers.values() if t.status == status])
                for status in TriggerStatus
            },
            "polling_tasks": len(self.polling_manager.polling_tasks),
            "scheduled_tasks": len(self.scheduled_manager.scheduled_tasks),
            "webhooks": len(self.webhook_handler.webhooks)
        }

# Global trigger system
trigger_system = TriggerSystem()
