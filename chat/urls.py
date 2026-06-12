"""Chat REST API URL routing."""

from django.urls import path

from . import views

urlpatterns = [
    # Unread summary
    path("rooms/unread-summary/", views.UnreadSummaryView.as_view(), name="chat-unread-summary"),
    # Rooms
    path("rooms/", views.RoomListCreateView.as_view(), name="chat-room-list-create"),
    path("rooms/<uuid:room_id>/", views.RoomDetailView.as_view(), name="chat-room-detail"),
    # Messages
    path("rooms/<uuid:room_id>/messages/", views.MessageListView.as_view(), name="chat-message-list"),
    path("rooms/<uuid:room_id>/messages/send/", views.MessageCreateView.as_view(), name="chat-message-create"),
    # Attachments
    path("rooms/<uuid:room_id>/attachments/", views.AttachmentUploadView.as_view(), name="chat-attachment-upload"),
    # Price offers
    path("rooms/<uuid:room_id>/price-offers/", views.PriceOfferCreateView.as_view(), name="chat-price-offer-create"),
    path("rooms/<uuid:room_id>/price-offers/<uuid:message_id>/accept/", views.PriceOfferAcceptView.as_view(), name="chat-price-offer-accept"),
    # Room actions
    path("rooms/<uuid:room_id>/mark-read/", views.MarkRoomReadView.as_view(), name="chat-room-mark-read"),
    path("rooms/<uuid:room_id>/close/", views.CloseRoomView.as_view(), name="chat-room-close"),
    path("rooms/<uuid:room_id>/link-contract/", views.LinkContractView.as_view(), name="chat-room-link-contract"),
]
