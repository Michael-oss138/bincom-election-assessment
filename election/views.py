from datetime import datetime
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from .models import LGA, Ward, PollingUnit, Party, AnnouncedPUResult

DELTA_STATE_ID = 25


def home(request):
    return render(request, 'election/home.html')


def polling_unit_results(request):
    # Only polling units in the Delta State dataset are relevant.
    lgas = LGA.objects.filter(state_id=DELTA_STATE_ID)
    selected_id = request.GET.get('polling_unit')
    selected_unit = None
    results = []
    total_votes = 0
    if selected_id:
        try:
            selected_unit = PollingUnit.objects.get(uniqueid=int(selected_id))
            # Ensure the selected unit belongs to an LGA in Delta State.
            if not lgas.filter(lga_id=selected_unit.lga_id).exists():
                selected_unit = None
                messages.error(request, 'Please select a valid Delta State polling unit.')
            else:
                results = list(AnnouncedPUResult.objects.filter(
                    polling_unit_uniqueid=str(selected_unit.uniqueid)
                ).order_by('party_abbreviation'))
                total_votes = sum(row.party_score for row in results)
        except (ValueError, PollingUnit.DoesNotExist):
            messages.error(request, 'The selected polling unit was not found.')
    units = PollingUnit.objects.filter(lga_id__in=lgas.values_list('lga_id', flat=True))
    return render(request, 'election/polling_unit_results.html', {
        'units': units, 'selected_unit': selected_unit,
        'results': results, 'total_votes': total_votes,
    })


def lga_results(request):
    lgas = LGA.objects.filter(state_id=DELTA_STATE_ID)
    selected_id = request.GET.get('lga')
    selected_lga = None
    results = []
    total_votes = 0
    if selected_id:
        try:
            selected_lga = lgas.get(lga_id=int(selected_id))
            # Deliberately aggregate announced_pu_results, NOT announced_lga_results.
            results = list(AnnouncedPUResult.objects.filter(
                polling_unit_uniqueid__in=PollingUnit.objects.filter(
                    lga_id=selected_lga.lga_id
                ).values_list('uniqueid', flat=True)
            ).values('party_abbreviation').annotate(
                total_votes=Sum('party_score')
            ).order_by('party_abbreviation'))
            total_votes = sum(row['total_votes'] or 0 for row in results)
        except (ValueError, LGA.DoesNotExist):
            messages.error(request, 'Please select a valid local government area.')
    return render(request, 'election/lga_results.html', {
        'lgas': lgas, 'selected_lga': selected_lga,
        'results': results, 'total_votes': total_votes,
    })


@require_http_methods(['GET', 'POST'])
def enter_results(request):
    lgas = LGA.objects.filter(state_id=DELTA_STATE_ID)
    lga_id = request.POST.get('lga') or request.GET.get('lga') or ''
    ward_id = request.POST.get('ward') or request.GET.get('ward') or ''
    unit_id = request.POST.get('polling_unit') or request.GET.get('polling_unit') or ''
    wards = Ward.objects.none()
    units = PollingUnit.objects.none()
    if lga_id.isdigit():
        # In this legacy dataset ward.lga_id and polling_unit.lga_id store lga.lga_id.
        wards = Ward.objects.filter(lga_id=int(lga_id))
        units = PollingUnit.objects.filter(lga_id=int(lga_id))
    if ward_id.isdigit():
        units = units.filter(ward_id=Ward.objects.filter(
            uniqueid=int(ward_id), lga_id=int(lga_id) if lga_id.isdigit() else -1
        ).values_list('ward_id', flat=True).first())

    parties = Party.objects.all()
    if request.method == 'POST':
        if not (lga_id.isdigit() and ward_id.isdigit() and unit_id.isdigit()):
            messages.error(request, 'Select an LGA, ward, and polling unit before submitting.')
        else:
            try:
                lga = lgas.get(lga_id=int(lga_id))
                ward = wards.get(uniqueid=int(ward_id))
                unit = PollingUnit.objects.get(uniqueid=int(unit_id), lga_id=lga.lga_id)
                if unit.ward_id != ward.ward_id:
                    raise PollingUnit.DoesNotExist
                scores = []
                for party in parties:
                    raw = request.POST.get(f'score_{party.partyid}', '0').strip()
                    score = int(raw or '0')
                    if score < 0:
                        raise ValueError('Vote counts cannot be negative.')
                    abbreviation = 'LABO' if party.partyid == 'LP' else party.partyid
                    scores.append((abbreviation, score))
                now = datetime.now()
                ip = request.META.get('REMOTE_ADDR', '')[:50]
                username = request.POST.get('entered_by_user', 'Web User').strip()[:50] or 'Web User'
                # Keep all party rows in a single transaction. Avoid duplicates by
                # refusing to overwrite existing results for this polling unit.
                if AnnouncedPUResult.objects.filter(
                    polling_unit_uniqueid=str(unit.uniqueid)
                ).exists():
                    messages.error(request, 'This polling unit already has results. This form only adds results for a unit with no existing result rows.')
                else:
                    with transaction.atomic():
                        AnnouncedPUResult.objects.bulk_create([
                            AnnouncedPUResult(
                                polling_unit_uniqueid=str(unit.uniqueid),
                                party_abbreviation=abbr,
                                party_score=score,
                                entered_by_user=username,
                                date_entered=now,
                                user_ip_address=ip,
                            ) for abbr, score in scores
                        ])
                    messages.success(request, 'Results for all parties were saved successfully.')
                    return redirect('enter_results')
            except (ValueError, LGA.DoesNotExist, Ward.DoesNotExist, PollingUnit.DoesNotExist) as exc:
                messages.error(request, f'Could not save results: {exc}')
    return render(request, 'election/enter_results.html', {
        'lgas': lgas, 'wards': wards, 'units': units, 'parties': parties,
        'selected_lga': lga_id, 'selected_ward': ward_id,
        'selected_unit': unit_id,
    })
