from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from account.models import KYC
from core.models import Transaction
import face_recognition
import numpy as np
from django.views.decorators.csrf import csrf_exempt,csrf_protect
import base64
from django.http import JsonResponse
import logging
from django.urls import reverse
import os 
from PIL import Image
from io import BytesIO
import json
from core.services import FaceVerificationService


from django.contrib.auth.decorators import login_required


# os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

import cv2

logger=logging.getLogger(__name__)

# Create your views here.

#email

@csrf_protect
@login_required
def verify_face_transaction(request):
    """Final robust face verification endpoint"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST allowed'}, status=405)

    try:
        # Debug raw request data
        print("Raw content type:", request.content_type)
        print("Raw body:", request.body[:200])  # First 200 chars

        # Handle both JSON and form-data
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body.decode('utf-8'))
            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid JSON',
                    'error': str(e)
                }, status=400)
        else:  # form-data
            data = request.POST.dict()

        print("Parsed data:", data)

        # Validate required fields
        required = ['account_number', 'transaction_id', 'face_data']
        if not all(k in data for k in required):
            return JsonResponse({
                'status': 'error',
                'message': 'Missing parameters',
                'required': required,
                'received': list(data.keys())
            }, status=400)

        # Process image
        try:
            face_data = data['face_data']
            if face_data.startswith('data:image'):
                face_data = face_data.split(',')[1]
            
            img = Image.open(BytesIO(base64.b64decode(face_data)))
            rgb_img = np.array(img)
            if rgb_img.ndim == 3 and rgb_img.shape[2] == 4:
                rgb_img = rgb_img[:, :, :3]
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': 'Image processing failed',
                'error': str(e)
            }, status=400)

        # Face verification logic
        kyc = request.user.kyc
        stored_encoding = np.array(kyc.face_encoding.split(','), dtype=float)
        face_locations = face_recognition.face_locations(rgb_img)
        
        if not face_locations:
            return JsonResponse({
                'status': 'error',
                'message': 'No face detected'
            }, status=400)

        current_encoding = face_recognition.face_encodings(rgb_img, face_locations)[0]
        match = face_recognition.compare_faces([stored_encoding], current_encoding)

        if not match[0]:
            return JsonResponse({
                'status': 'error',
                'message': 'Face verification failed'
            }, status=400)

        # Update transaction
        Transaction.objects.filter(
            transaction_id=data['transaction_id'],
            sender_account__account_number=data['account_number']
        ).update(
            verification_method='FACE',
            face_verification_status=True,
            status='completed'
        )

        return JsonResponse({
            'status': 'success',
            'redirect': reverse('core:transfer-completed', args=[
                data['account_number'],
                data['transaction_id']
            ])
        })

    except Exception as e:
        print("Full error:", str(e))
        return JsonResponse({
            'status': 'error',
            'message': 'Server error',
            'error': str(e)
        }, status=500)

# @csrf_exempt
# def verify_face_transaction(request):
#     """Handle face verification for transactions using browser-captured images"""
#     if request.method != 'POST':
#         return JsonResponse({'error': 'Only POST requests allowed'}, status=405)

#     try:
#         # Parse JSON data from request body
#         try:
#             data = json.loads(request.body.decode('utf-8'))
#             account_number = data.get('account_number')
#             transaction_id = data.get('transaction_id')
#             face_data = data.get('face_data')
#         except json.JSONDecodeError:
#             return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        
#         if not all([account_number, transaction_id, face_data]):
#             return JsonResponse({'error': 'Missing parameters'}, status=400)

#         # Verify user and KYC
#         user = request.user
#         if not user.is_authenticated:
#             return JsonResponse({'error': 'Authentication required'}, status=403)

#         try:
#             kyc = KYC.objects.get(user=user)
#             if not kyc.face_encoding:
#                 return JsonResponse({
#                     'success': False,
#                     'error': 'No face data available',
#                     'redirect': reverse('account:kyc-reg')
#                 }, status=400)
#         except KYC.DoesNotExist:
#             return JsonResponse({
#                 'success': False,
#                 'error': 'KYC not completed',
#                 'redirect': reverse('account:kyc-reg')
#             }, status=400)

#         # Process base64 image
#         try:
#             # Handle both data:image and raw base64
#             if face_data.startswith('data:image'):
#                 header, encoded = face_data.split(',', 1)
#             else:
#                 encoded = face_data
                
#             img_bytes = base64.b64decode(encoded)
#             img = Image.open(BytesIO(img_bytes))
#             rgb_img = np.array(img)
            
#             # Convert from RGBA to RGB if needed
#             if rgb_img.ndim == 3 and rgb_img.shape[2] == 4:
#                 rgb_img = rgb_img[:, :, :3]
#         except Exception as e:
#             logger.error(f"Image processing error: {str(e)}")
#             return JsonResponse({
#                 'success': False,
#                 'error': 'Invalid image format'
#             }, status=400)

#         # Face detection
#         face_locations = face_recognition.face_locations(rgb_img)
#         if not face_locations:
#             return JsonResponse({
#                 'success': False,
#                 'error': 'No face detected',
#                 'retry': True
#             }, status=400)

#         if len(face_locations) > 1:
#             return JsonResponse({
#                 'success': False,
#                 'error': 'Multiple faces detected',
#                 'retry': True
#             }, status=400)

#         # Face verification
#         stored_encoding = np.array([float(x) for x in kyc.face_encoding.split(',')])
#         current_encoding = face_recognition.face_encodings(rgb_img, known_face_locations=face_locations)[0]
        
#         match = face_recognition.compare_faces([stored_encoding], current_encoding, tolerance=0.45)
        
#         if not match[0]:
#             return JsonResponse({
#                 'success': False,
#                 'error': 'Face verification failed',
#                 'retry': True
#             }, status=400)

#         # Update transaction
#         transaction = Transaction.objects.get(
#             transaction_id=transaction_id,
#             sender_account__account_number=account_number
#         )
#         transaction.verification_method = 'FACE'
#         transaction.face_verification_status = True
#         transaction.status = 'completed'
#         transaction.save()

#         return JsonResponse({
#             'success': True,
#             'redirect': reverse('core:transfer-completed', args=[account_number, transaction_id])
#         })

#     except Transaction.DoesNotExist:
#         return JsonResponse({'error': 'Transaction not found'}, status=404)
#     except Exception as e:
#         logger.error(f"Verification error: {str(e)}")
#         return JsonResponse({
#             'success': False,
#             'error': 'System error during verification',
#             'retry': False
#         }, status=500)

# @csrf_exempt
# def verify_face_transaction(request):
#     """Handle face verification for transactions using browser-captured images"""
#     if request.method != 'POST':
#         return JsonResponse({'error': 'Only POST requests allowed'}, status=405)

#     try:
#         # Get required parameters
#         account_number = request.POST.get('account_number')
#         transaction_id = request.POST.get('transaction_id')
#         face_data = request.POST.get('face_data')
        
#         if not all([account_number, transaction_id, face_data]):
#             return JsonResponse({'error': 'Missing parameters'}, status=400)

#         # Verify user and KYC
#         user = request.user
#         if not user.is_authenticated:
#             return JsonResponse({'error': 'Authentication required'}, status=403)

#         try:
#             kyc = KYC.objects.get(user=user)
#             if not kyc.face_encoding:
#                 return JsonResponse({
#                     'success': False,
#                     'error': 'No face data available',
#                     'redirect': reverse('account:kyc-reg')
#                 })
#         except KYC.DoesNotExist:
#             return JsonResponse({
#                 'success': False,
#                 'error': 'KYC not completed',
#                 'redirect': reverse('account:kyc-reg')
#             })

#         # Process base64 image
#         try:
#             header, encoded = face_data.split(',', 1)
#             img_bytes = base64.b64decode(encoded)
#             img = Image.open(BytesIO(img_bytes))
#             rgb_img = np.array(img)
            
#             # Convert from RGBA to RGB if needed
#             if rgb_img.shape[2] == 4:
#                 rgb_img = rgb_img[:, :, :3]
#         except Exception as e:
#             logger.error(f"Image processing error: {str(e)}")
#             return JsonResponse({
#                 'success': False,
#                 'error': 'Invalid image format'
#             })

#         # Face detection
#         face_locations = face_recognition.face_locations(rgb_img)
#         if not face_locations:
#             return JsonResponse({
#                 'success': False,
#                 'error': 'No face detected',
#                 'retry': True
#             })

#         if len(face_locations) > 1:
#             return JsonResponse({
#                 'success': False,
#                 'error': 'Multiple faces detected',
#                 'retry': True
#             })

#         # Face verification
#         stored_encoding = np.array([float(x) for x in kyc.face_encoding.split(',')])
#         current_encoding = face_recognition.face_encodings(rgb_img, known_face_locations=face_locations)[0]
        
#         match = face_recognition.compare_faces([stored_encoding], current_encoding, tolerance=0.45)
        
#         if not match[0]:
#             return JsonResponse({
#                 'success': False,
#                 'error': 'Face verification failed',
#                 'retry': True
#             })

#         # Update transaction
#         transaction = Transaction.objects.get(
#             transaction_id=transaction_id,
#             sender_account__account_number=account_number
#         )
#         transaction.verification_method = 'FACE'
#         transaction.face_verification_status = True
#         transaction.status = 'completed'
#         transaction.save()

#         return JsonResponse({
#             'success': True,
#             'redirect': reverse('core:transfer-completed', args=[account_number, transaction_id])
#         })

#     except Transaction.DoesNotExist:
#         return JsonResponse({'error': 'Transaction not found'}, status=404)
#     except Exception as e:
#         logger.error(f"Verification error: {str(e)}")
#         return JsonResponse({
#             'success': False,
#             'error': 'System error during verification',
#             'retry': False
#         })
@csrf_exempt
def verify_face(request):
    """
    Handle face verification from both webcam capture and file upload
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests allowed'}, status=405)

    try:
        # Get user and check KYC
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=403)

        try:
            kyc = KYC.objects.get(user=user)
            if not kyc.face_encoding:
                return JsonResponse({
                    'success': False,
                    'error': 'No face data available',
                    'redirect': reverse('account:kyc-reg')
                })
        except KYC.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'KYC not completed',
                'redirect': reverse('account:kyc-reg')
            })

        # Process image data
        if 'face_data' in request.POST:
            # Handle base64 image from webcam
            try:
                image_data = request.POST['face_data'].split(',')[1]
                img_bytes = base64.b64decode(image_data)
                img = Image.open(BytesIO(img_bytes))
                rgb_img = np.array(img)
            except Exception as e:
                logger.error(f"Image processing error: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid image format'
                })
        else:
            # Handle file upload
            if 'face_image' not in request.FILES:
                return JsonResponse({
                    'success': False,
                    'error': 'No image provided'
                })
            
            try:
                img_bytes = request.FILES['face_image'].read()
                img = Image.open(BytesIO(img_bytes))
                rgb_img = np.array(img)
            except Exception as e:
                logger.error(f"Image upload error: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to process uploaded image'
                })

        # Face detection
        face_locations = face_recognition.face_locations(rgb_img)
        if not face_locations:
            return JsonResponse({
                'success': False,
                'error': 'No face detected',
                'retry': True
            })

        if len(face_locations) > 1:
            return JsonResponse({
                'success': False,
                'error': 'Multiple faces detected',
                'retry': True
            })

        # Face verification
        stored_encoding = np.array([float(x) for x in kyc.face_encoding.split(',')])
        current_encoding = face_recognition.face_encodings(rgb_img, known_face_locations=face_locations)[0]
        
        match = face_recognition.compare_faces([stored_encoding], current_encoding, tolerance=0.45)
        
        if not match[0]:
            return JsonResponse({
                'success': False,
                'error': 'Face verification failed',
                'retry': True
            })

        # Success case
        return JsonResponse({
            'success': True,
            'redirect': request.POST.get('next', reverse('account:dashboard'))
        })

    except Exception as e:
        logger.error(f"Verification error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'System error during verification',
            'retry': False
        })

# def verify_face(request):
#     # --- Error Handling ---
#     if not request.method == 'POST':
#         return JsonResponse({'error': 'Only POST requests allowed'}, status=405)

#     if not request.user.is_authenticated:
#         return JsonResponse({'error': 'Authentication required'}, status=403)
    
    

#     try:
#         # --- Image Processing ---
#         # 1. Get base64 image data
#         image_data = request.POST.get('face_data', '').split(',')
#         if len(image_data) != 2:
#             return JsonResponse({'error': 'Invalid image format'}, status=400)

#         # 2. Decode image
#         img_bytes = base64.b64decode(image_data[1])
#         nparr = np.frombuffer(img_bytes, np.uint8)
#         img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
#         if img is None:
#             return JsonResponse({'error': 'Failed to decode image'}, status=400)

#         # --- Face Detection ---
#         # 3. Convert to RGB and enhance
#         rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#         rgb_img = cv2.resize(rgb_img, (0, 0), fx=1.2, fy=1.2)  # Improve small faces
        
#         # 4. Multiple detection methods
#         face_locations = face_recognition.face_locations(rgb_img, model="hog")  # Faster
#         if not face_locations:
#             face_locations = face_recognition.face_locations(rgb_img, model="cnn")  # Slower but more accurate

#         if not face_locations:
#             return JsonResponse({
#                 'success': False,
#                 'error': 'No face detected. Ensure: 1) Good lighting 2) Face is centered 3) No obstructions',
#                 'retry': True
#             })

#         # --- Face Verification ---
#         # 5. Get user's stored face encoding
#         try:
#             kyc = request.user.kyc
#             stored_encoding = np.array([float(x) for x in kyc.face_encoding.split(',')])
#         except Exception as e:
#             return JsonResponse({
#                 'success': False,
#                 'error': 'No face data available. Please update your KYC profile.',
#                 'fallback': reverse('account:kyc-reg')
#             })

#         # 6. Compare faces
#         current_encoding = face_recognition.face_encodings(rgb_img, face_locations)[0]
#         match = face_recognition.compare_faces([stored_encoding], current_encoding, tolerance=0.45)

#         if not match[0]:
#             return JsonResponse({
#                 'success': False,
#                 'error': 'Face verification failed. Please try again or use PIN.',
#                 'retry': True
#             })

#         # --- Success Case ---
#         # 7. Update transaction
#         transaction_id = request.POST.get('transaction_id')
#         if transaction_id:
#             Transaction.objects.filter(transaction_id=transaction_id).update(
#                 verification_method='FACE',
#                 face_verification_status=True
#             )

#         return JsonResponse({
#             'success': True,
#             'redirect': reverse('core:transfer-completed', args=[transaction_id])
#         })

#     # except Exception as e:
#     #     logger.error(f"Face verification error: {str(e)}")
#     #     return JsonResponse({
#     #         'success': False,
#     #         'error': 'System error. Please try again later.',
#     #         'retry': False
#     #     }, status=500)

#     except Exception as e:
#         logger.error(f"Verification error: {str(e)}")
#         return JsonResponse({
#             'success': False,
#             'error': 'Verification service unavailable. Please try PIN.'
#         }, status=500)
    
    

# def verify_face(request):
#     if not request.user.is_authenticated:
#         return redirect('userauths:sign-in')
    
#     try:
#         kyc = KYC.objects.get(user=request.user)
#     except KYC.DoesNotExist:
#         messages.warning(request, "KYC not completed. Please submit your KYC first.")
#         return redirect('account:kyc-reg')
    
#     if not kyc.face_encoding:
#         messages.warning(request, "Face data not available. Please update your KYC profile picture.")
#         return redirect('account:kyc-reg')
    
#     if request.method == 'POST':
#         # Capture image from webcam
#         webcam = cv2.VideoCapture(0)
#         ret, frame = webcam.read()
#         webcam.release()
        
#         if not ret:
#             messages.error(request, "Failed to capture image. Please try again.")
#             return redirect('core:face-verification')
        
#         try:
#             # Process images
#             stored_encoding = np.array([float(x) for x in kyc.face_encoding.split(',')])
#             captured_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#             captured_encoding = face_recognition.face_encodings(captured_image)
            
#             if not captured_encoding:
#                 messages.error(request, "No face detected. Please ensure your face is clearly visible.")
#                 return redirect('core:face-verification')
            
#             # Compare faces
#             match = face_recognition.compare_faces(
#                 [stored_encoding],
#                 captured_encoding[0],
#                 tolerance=0.45
#             )
            
#             if match[0]:
#                 request.session['face_verified'] = True
#                 next_url = request.GET.get('next', 'account:dashboard')
#                 return redirect(next_url)
#             else:
#                 messages.error(request, "Face verification failed. Please try again.")
#         except Exception as e:
#             messages.error(request, f"Error during verification: {str(e)}")
    
#     return render(request, 'core/face_verification.html')


def handling_404(request, exception):
    return render(request, 'core/404.html', {})

def new_useremail(request):
    return render(request, "email/register_email.html")

def trans_email(request):
    return render(request, "email/trans_email.html")

def index(request):
    return render(request, 'core/index.html')

def comingsoon(request):
    return render(request, 'core/coming-soon.html')

def aboutus(request):
    return render(request, 'core/about-us.html')