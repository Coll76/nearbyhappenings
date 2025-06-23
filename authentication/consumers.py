import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync

class NotificationConsumer(WebsocketConsumer):
    def connect(self):
        self.user = self.scope["user"]

        if self.user.is_authenticated:
            # Add user to personal group
            self.user_group_name = f"user_{self.user.id}"
            async_to_sync(self.channel_layer.group_add)(
                self.user_group_name, self.channel_name
            )

            # Add admin to admin group
            if self.user.is_staff:
                async_to_sync(self.channel_layer.group_add)(
                    "admin_notifications", self.channel_name
                )

            self.accept()

    def disconnect(self, close_code):
        # Remove from all groups
        if hasattr(self, 'user_group_name'):
            async_to_sync(self.channel_layer.group_discard)(
                self.user_group_name, self.channel_name
            )

        if self.user.is_staff:
            async_to_sync(self.channel_layer.group_discard)(
                "admin_notifications", self.channel_name
            )

    # Notification handlers
    def planner_notification(self, event):
        self.send(text_data=json.dumps({
            'type': 'planner_notification',
            'message': event['message'],
            'planner_id': event['planner_id']
        }))

    def planner_status(self, event):
        self.send(text_data=json.dumps({
            'type': 'status_update',
            'status': event['status'],
            'message': event['message']
        }))

