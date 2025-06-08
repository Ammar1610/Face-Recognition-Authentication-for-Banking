from django import forms
from django.core.exceptions import ValidationError
from .models import KYC
import face_recognition
import numpy as np
import cv2

class FaceVerificationForm(forms.Form):
    face_image = forms.ImageField()
    
    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        if not self.user:
            raise ValidationError("User not found")
        
        try:
            kyc = KYC.objects.get(user=self.user)
        except KYC.DoesNotExist:
            raise ValidationError("KYC not submitted")
        
        if not kyc.face_encoding:
            raise ValidationError("No face data available for verification")
        
        uploaded_image = cleaned_data.get('face_image')
        if not uploaded_image:
            raise ValidationError("No image provided")
        
        # Process uploaded image
        try:
            # Convert InMemoryUploadedFile to numpy array
            image_stream = uploaded_image.read()
            image_array = np.frombuffer(image_stream, np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            # Find faces in the uploaded image
            face_locations = face_recognition.face_locations(image)
            if len(face_locations) != 1:
                raise ValidationError("Please ensure only one face is visible")
            
            # Get face encoding
            uploaded_encoding = face_recognition.face_encodings(image, known_face_locations=face_locations)[0]
            
            # Get stored encoding
            stored_encoding = np.array(list(map(float, kyc.face_encoding.split(','))))
            
            # Compare faces
            match = face_recognition.compare_faces([stored_encoding], uploaded_encoding, tolerance=0.45)
            
            if not match[0]:
                raise ValidationError("Face verification failed")
            
        except Exception as e:
            raise ValidationError(f"Error processing image: {str(e)}")
        
        return cleaned_data