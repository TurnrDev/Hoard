from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST

from .models import CampaignContext, Character

MAX_CAH_UPLOAD_BYTES = 5 * 1024 * 1024


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
