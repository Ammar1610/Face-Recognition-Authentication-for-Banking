from django.shortcuts import render, redirect
from django.urls import reverse
from core.models import Transaction
from account.models import Account, KYC
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
import face_recognition
import numpy as np
import json
from django.views.decorators.csrf import csrf_exempt
import base64
from io import BytesIO
from PIL import Image
import logging

from core.models import Recipient, Notification

logger = logging.getLogger(__name__)

@login_required
def transaction_list(request):
    sender_transaction = Transaction.objects.filter(sender=request.user).order_by("-id")
    reciever_transaction = Transaction.objects.filter(reciever=request.user).order_by("-id")
    request_sender_transaction = Transaction.objects.filter(sender=request.user, transaction_type="request")
    request_reciever_transaction = Transaction.objects.filter(reciever=request.user, transaction_type="request")

    context = {
        "sender_transaction": sender_transaction,
        "reciever_transaction": reciever_transaction,
        "request_sender_transaction": request_sender_transaction,
        "request_reciever_transaction": request_reciever_transaction
    }
    return render(request, "transaction/transaction-list.html", context)

@csrf_exempt
@login_required
def verify_face_and_process_transaction(request):
    if request.method == "POST":
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body.decode('utf-8'))
            else:
                data = request.POST.dict()

            required_fields = ['account_number', 'transaction_id', 'face_data']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Missing fields: {", ".join(missing_fields)}'
                }, status=400)

            try:
                transaction = Transaction.objects.get(
                    transaction_id=data['transaction_id'],
                    sender=request.user
                )
            except Transaction.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Transaction not found or not authorized'
                }, status=404)

            image_data = data.get('face_data')
            if not image_data:
                return JsonResponse({'status': 'error', 'message': 'No image data provided'}, status=400)

            if image_data.startswith('data:image'):
                header, encoded = image_data.split(',', 1)
            else:
                encoded = image_data

            img_bytes = base64.b64decode(encoded)
            img = Image.open(BytesIO(img_bytes))
            rgb_img = np.array(img)

            kyc = request.user.kyc
            stored_encoding = np.array(kyc.face_encoding.split(','), dtype=float)
            face_locations = face_recognition.face_locations(rgb_img)

            if not face_locations:
                return JsonResponse({'status': 'error', 'message': 'No face detected'}, status=400)

            current_encoding = face_recognition.face_encodings(rgb_img, face_locations)[0]
            match = face_recognition.compare_faces([stored_encoding], current_encoding)

            if not match[0]:
                return JsonResponse({'status': 'error', 'message': 'Face verification failed'}, status=400)

            # Perform transaction logic
            receiver_account = Account.objects.get(account_number=data['account_number'])
            sender_account = request.user.account
            receiver = receiver_account.user
            receiver_kyc = receiver.kyc
            full_name = receiver_kyc.full_name
            amount = transaction.amount

            # Update balances
            sender_account.account_balance -= amount
            sender_account.save()

            receiver_account.account_balance += amount
            receiver_account.save()

            # Mark transaction as completed
            transaction.verification_method = 'FACE'
            transaction.face_verification_status = True
            transaction.status = 'completed'
            transaction.save()

            # Create or update Recipient
            account_type = 'NGN'
            recipient, created = Recipient.objects.get_or_create(
                kyc=receiver_kyc,
                account_type=account_type,
                defaults={
                    'r_number': receiver_account.account_number,
                    'user': request.user,
                    'full_name': full_name,
                    'account_type': 'NGN'
                }
            )
            if not created:
                recipient.r_number = receiver_account.account_number
                recipient.user = request.user
                recipient.full_name = full_name
                recipient.account_type = 'NGN'
                recipient.save()

            # Notifications
            Notification.objects.create(
                amount=amount,
                user=receiver,
                notification_type="Credit Alert",
                currency="NGN"
            )

            Notification.objects.create(
                amount=amount,
                user=request.user,
                notification_type="Debit Alert",
                currency="NGN"
            )

            return JsonResponse({
                'status': 'success',
                'message': 'Face verified and transaction completed successfully',
                'redirect': reverse('core:transfer-completed', args=[
                    data['account_number'],
                    data['transaction_id']
                ])
            })

        except Exception as e:
            logger.error(f"Error in face verification: {str(e)}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


# @csrf_exempt
# @login_required
# def verify_face_and_process_transaction(request):
#     if request.method == "POST":
#         try:
#             # Parse JSON or form data
#             if request.content_type == 'application/json':
#                 data = json.loads(request.body.decode('utf-8'))
#             else:
#                 data = request.POST.dict()

#             # Validate required fields
#             required_fields = ['account_number', 'transaction_id', 'face_data']
#             missing_fields = [field for field in required_fields if field not in data]
#             if missing_fields:
#                 return JsonResponse({
#                     'status': 'error',
#                     'message': f'Missing fields: {", ".join(missing_fields)}'
#                 }, status=400)

#             # Get transaction
#             try:
#                 transaction = Transaction.objects.get(
#                     transaction_id=data['transaction_id'],
#                     sender=request.user
#                 )
#             except Transaction.DoesNotExist:
#                 return JsonResponse({
#                     'status': 'error',
#                     'message': 'Transaction not found or not authorized'
#                 }, status=404)

#             # Process image data
#             image_data = data.get('face_data')
#             if not image_data:
#                 return JsonResponse({'status': 'error', 'message': 'No image data provided'}, status=400)

#             # Process image - handle both data:image and raw base64
#             if image_data.startswith('data:image'):
#                 header, encoded = image_data.split(',', 1)
#             else:
#                 encoded = image_data

#             img_bytes = base64.b64decode(encoded)
#             img = Image.open(BytesIO(img_bytes))
#             rgb_img = np.array(img)

#             # Verify face
#             kyc = request.user.kyc
#             stored_encoding = np.array(kyc.face_encoding.split(','), dtype=float)
#             face_locations = face_recognition.face_locations(rgb_img)
            
#             if not face_locations:
#                 return JsonResponse({
#                     'status': 'error',
#                     'message': 'No face detected'
#                 }, status=400)

#             current_encoding = face_recognition.face_encodings(rgb_img, face_locations)[0]
#             match = face_recognition.compare_faces([stored_encoding], current_encoding)

#             if not match[0]:
#                 return JsonResponse({
#                     'status': 'error',
#                     'message': 'Face verification failed'
#                 }, status=400)

#             # Update transaction
#             transaction.verification_method = 'FACE'
#             transaction.face_verification_status = True
#             transaction.status = 'completed'
#             transaction.save()

#             return JsonResponse({
#                 'status': 'success',
#                 'message': 'Face verified successfully',
#                 'redirect': reverse('core:transfer-completed', args=[
#                     data['account_number'],
#                     data['transaction_id']
#                 ])
#             })

#         except Exception as e:
#             logger.error(f"Error in face verification: {str(e)}", exc_info=True)
#             return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

#     return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


@login_required
def transaction_detail(request, transaction_id):
    transaction = Transaction.objects.get(transaction_id=transaction_id)
    context = {"transaction": transaction}
    return render(request, "transaction/transaction-detail.html", context)