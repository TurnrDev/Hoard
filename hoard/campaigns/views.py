from uuid import uuid4

from django.core.cache import cache
from django.core.files.base import ContentFile
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST

from .models import CampaignContext, Character
from .realtime import notify_campaign_changed

MAX_CAH_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_PORTRAIT_UPLOAD_BYTES = 5 * 1024 * 1024


@require_POST
def cah_upload(request, upload_id: str):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required."}, status=401)
    metadata = cache.get(f"cah-upload:{upload_id}")
    if (
        not metadata
        or metadata.get("user_id") != request.user.pk
        or metadata.get("transferred")
    ):
        return JsonResponse({"detail": "Upload not found or expired."}, status=404)
    context = CampaignContext.objects.filter(
        pk=metadata.get("context_id"),
        campaign_id=metadata.get("campaign_id"),
        user=request.user,
        is_active=True,
    ).first()
    if (
        context is None
        or not Character.objects.filter(
            pk=metadata.get("character_id"), campaign_id=context.campaign_id
        ).exists()
    ):
        return JsonResponse(
            {"detail": "Upload target is no longer available."}, status=404
        )
    uploaded = request.FILES.get("file")
    if uploaded is None or not uploaded.name.lower().endswith(".cah"):
        return JsonResponse({"detail": "Upload a .cah file."}, status=422)
    if uploaded.size > MAX_CAH_UPLOAD_BYTES:
        return JsonResponse({"detail": "The .cah file exceeds 5 MiB."}, status=413)
    raw = uploaded.read(MAX_CAH_UPLOAD_BYTES + 1)
    if len(raw) > MAX_CAH_UPLOAD_BYTES:
        return JsonResponse({"detail": "The .cah file exceeds 5 MiB."}, status=413)
    cache.set(f"cah-upload-bytes:{upload_id}", raw, timeout=900)
    metadata["transferred"] = True
    cache.set(f"cah-upload:{upload_id}", metadata, timeout=900)
    return HttpResponse(status=204)


@require_POST
def character_portrait_upload(request, context_id: int, character_id: int):
    """Store an authenticated character portrait and return its media URL."""
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required."}, status=401)
    context = CampaignContext.objects.filter(
        pk=context_id,
        user=request.user,
        is_active=True,
    ).first()
    if context is None:
        return JsonResponse({"detail": "Campaign context not found."}, status=404)
    character = Character.objects.filter(
        pk=character_id,
        campaign_id=context.campaign_id,
    ).first()
    if character is None:
        return JsonResponse({"detail": "Character not found."}, status=404)
    owns_character = character.context_id == context.pk
    if context.kind != CampaignContext.Kind.GM and not owns_character:
        return JsonResponse({"detail": "You cannot edit this character."}, status=403)

    uploaded = request.FILES.get("file")
    if uploaded is None:
        return JsonResponse({"detail": "Choose a portrait image."}, status=422)
    if uploaded.size > MAX_PORTRAIT_UPLOAD_BYTES:
        return JsonResponse(
            {"detail": "Portraits must be no larger than 5 MB."}, status=413
        )
    image = uploaded.read(MAX_PORTRAIT_UPLOAD_BYTES + 1)
    if len(image) > MAX_PORTRAIT_UPLOAD_BYTES:
        return JsonResponse(
            {"detail": "Portraits must be no larger than 5 MB."}, status=413
        )
    image_types = {
        "jpg": image.startswith(b"\xff\xd8\xff"),
        "png": image.startswith(b"\x89PNG\r\n\x1a\n"),
        "webp": image.startswith(b"RIFF") and image[8:12] == b"WEBP",
    }
    extension = next((name for name, matches in image_types.items() if matches), None)
    if extension is None:
        return JsonResponse(
            {"detail": "Portraits must be PNG, JPEG, or WebP images."},
            status=422,
        )

    previous_name = character.portrait.name
    character.portrait.save(
        f"{uuid4().hex}.{extension}",
        ContentFile(image),
        save=True,
    )
    if previous_name and previous_name != character.portrait.name:
        character.portrait.storage.delete(previous_name)
    notify_campaign_changed(context.campaign_id)

    return JsonResponse({"portrait_url": character.portrait.url})
