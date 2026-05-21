from django.shortcuts import render
import os,base64,httpx
from django.db.models import Count
# Create your views here.
from coreapp.paginations import StandardPagination
from coreapp.mixins import StandardResponseMixin,extract_first_error
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser,FormParser,JSONParser
from .serializers import ScanHistorySerializer,ScanRequestSerializer, AiPersonalizationSerializer
from .models import ScanHistory,SUBJECT_CHOICES
from authapp.models import User
from profileapp.models import UserProfile

# def call_vision_ai(image_file, subject: str, question: str) -> str:
#     """
#     Sends image + subject + question to OpenAI Vision API (or compatible).
#     API key loaded from environment — never hardcoded.
#     Returns AI text response or raises ValueError on failure.
#     """
#     api_key = os.getenv('OPENAI_API_KEY')#❓❓❓user will be able to change ai modle so I've to change here 
#     if not api_key:
#         raise ValueError(
#             "AI service is not configured. "
#             "Please ask the administrator to set OPENAI_API_KEY."
#         )
#     #❓❓❓explain this 4 below line
#     # Read and base64-encode the image for the API
#     image_data = base64.b64encode(image_file.read()).decode('utf-8')
#     image_file.seek(0)  # reset file pointer so Django can save it after
 
#     # Determine MIME type from file name
#     ext = image_file.name.rsplit('.', 1)[-1].lower()
#     mime = f"image/{ext}" if ext in ('png', 'jpg', 'jpeg', 'gif', 'webp') else "image/jpeg"
 
#     # Craft system prompt based on subject filter
#     system_prompt = (
#         f"You are an expert {subject} tutor. "
#         f"Analyze the provided image and answer any questions clearly and step by step. "
#         f"Focus only on {subject}-related content."
#     )
 
#     user_message = question.strip() if question else f"Please explain this {subject} problem."
 
#     payload = {
#         "model": "gpt-4o",
#         "messages": [
#             {"role": "system", "content": system_prompt},
#             {
#                 "role": "user",
#                 "content": [
#                     {"type": "text", "text": user_message},
#                     {
#                         "type": "image_url",
#                         "image_url": {"url": f"data:{mime};base64,{image_data}"}
#                     }
#                 ]
#             }
#         ],
#         "max_tokens": 1500
#     }
 
#     # Synchronous HTTP call — for production, move to Celery background task
#     response = httpx.post(
#         "https://api.openai.com/v1/chat/completions",
#         headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
#         json=payload,
#         timeout=60.0
#     )
 
#     if response.status_code != 200:
#         raise ValueError(
#             f"AI service returned an error (status {response.status_code}). "
#             "Please try again later."
#         )
 
#     data = response.json()
#     return data['choices'][0]['message']['content']

import fitz  # PyMuPDF (for PDF)
from docx import Document


def extract_text_from_pdf(file_obj):
    file_bytes = file_obj.read()
    file_obj.seek(0)

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)


def extract_text_from_docx(file_obj):
    file_obj.seek(0)
    doc = Document(file_obj)
    return "\n".join(p.text for p in doc.paragraphs)


def call_ai(file_obj, subject: str, question: str, model="gpt-4o"):
    try:
        file_obj.seek(0)

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")

        ext = file_obj.name.rsplit(".", 1)[-1].lower()

        # ================= IMAGE =================
        if ext in ["png", "jpg", "jpeg", "webp", "gif"]:
            file_obj.seek(0)
            image_data = base64.b64encode(file_obj.read()).decode("utf-8")

            mime = f"image/{ext}"

            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": f"You are an expert {subject} tutor."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": question or f"Explain this {subject} problem."},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime};base64,{image_data}"}
                            }
                        ]
                    }
                ],
                "max_tokens": 1500
            }

        # ================= PDF =================
        elif ext == "pdf":
            try:
                file_bytes = file_obj.read()
                file_obj.seek(0)

                doc = fitz.open(stream=file_bytes, filetype="pdf")
                text = "\n".join(page.get_text() for page in doc)
            except Exception:
                raise ValueError("Invalid or corrupted PDF file")

            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": f"You are an expert {subject} tutor."},
                    {"role": "user", "content": f"{text}\n\nQuestion: {question}"}
                ],
                "max_tokens": 1500
            }

        # ================= DOCX =================
        elif ext == "docx":
            try:
                file_obj.seek(0)
                doc = Document(file_obj)
                text = "\n".join(p.text for p in doc.paragraphs)
            except Exception:
                raise ValueError("Invalid DOCX file")

            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": f"You are an expert {subject} tutor."},
                    {"role": "user", "content": f"{text}\n\nQuestion: {question}"}
                ],
                "max_tokens": 1500
            }

        else:
            raise ValueError("Unsupported file type")

        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=60.0
        )

        if response.status_code != 200:
            raise ValueError(f"AI error: {response.text}")

        return response.json()["choices"][0]["message"]["content"]

    except Exception as e:
        # IMPORTANT: convert ANY crash to controlled error
        raise ValueError(str(e))


#jekono view te atfirst, permision, perser class, then post method thakle sekhane serializer call with user requsted data, then serializer validation check, if valid then user data gula serailizer e pass kora, tarpor logic apply kora, then modle e save kora, tarpor success response dewa
class ScanView(StandardResponseMixin,APIView):
    """
    POST /scan/
    Upload an image with a subject filter → get AI explanation.
    Also saves scan to history and increments problems_solved counter.
    """
    permission_classes=[IsAuthenticated]
    parser_classes = [MultiPartParser,FormParser]
 
    def post(self,request):
        serializer=ScanRequestSerializer(data=request.data)#❓❓❓ is requst.data dictionary?

        if not serializer.is_valid():#❓❓❓from where this is_valid comes, I didn't create any is_valid on serailizers
            reason = extract_first_error(serializer.errors)#❓❓❓ what does serializers.errors contains, is it builtin
            return self.error_response(
                f"Scan Requst Invalid : {reason}",
                status_code=400,
                data=serializer.errors
            )

        # subject = serializer.validated_data['subject']
        #image=serializer.validated_data['image']
        image = serializer.validated_data.get('image')   # None if not provided
        file = serializer.validated_data.get('file')
        uploaded_file = image or file

        subject = serializer.validated_data.get('subject', 'general')
        question = serializer.validated_data.get('question', '')
        #question = serializer.validated_data('question','')#❓❓❓ why here ()?
        '''
        validated_data is a dictionary, not a function.
        So when you use (), Python thinks you're trying to call a dict → 

        That’s why you get:

        TypeError: 'dict' object is not callable
        
        '''
        # question = serializer.validated_data.get('question', '')

        # Call AI — catch any errors and return meaningful message
        try:
            #ai_response = call_vision_ai(image,subject,question)
            ai_response = call_ai(
                uploaded_file,
                subject,
                question
            )
        except ValueError as e:
            return self.error_response(str(e),status_code=503)#❓❓❓ why 503 why not others?
        except Exception:
            return self.error_response(
               "AI service is temporarily unavailable. Please try again in a moment.",
                status_code=503
            )
        
        scan=ScanHistory.objects.create(#❓❓❓ whenever I wrote modelname.objects.create, do I've to pass all the requeried field on the model to save? 
            user=request.user,
            subject=subject,
            image=image if image else None,
            file=file if file else None,
            question=question,
            ai_response=ai_response
        )

        from django.db.models import F
        UserProfile.objects.filter(user=request.user).update(
            problems_solved = F('problems_solved')+1
        )

        return self.success_response(
            {
                "scan_id": str(scan.id),
                "subject": subject,
                "ai_response": ai_response,
            },
            message="Image scanned and analyzed successfully.",
            status_code=201
        )


class ScanHistoryView(StandardResponseMixin, APIView):
    """
    GET /scan/history/?subject=math
    Returns paginated scan history for the logged-in user.
    Optional ?subject= filter.
    """
    permission_classes = [IsAuthenticated]
 
    def get(self, request):
        # Filter by owner — users never see each other's scans
        base_qs = ScanHistory.objects.filter(user=request.user)
        qs = base_qs
 
        subject = request.query_params.get('subject')
        if subject:
            qs = qs.filter(subject=subject)#❓❓❓ is qs object here?

        # Subject-wise totals for this user (works with or without subject filter)
        subject_summary = list(
            base_qs.values('subject')
            .annotate(total_images=Count('id'))
            .order_by('subject')
        )
 
        # only('id','subject','question','ai_response','created_at') avoids loading
        # the large image binary path unnecessarily — handled by get_image_url
        qs = qs.only('id', 'subject', 'image', 'question', 'ai_response', 'created_at')

        #❓❓❓ explain below 3 lines
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ScanHistorySerializer(page, many=True, context={'request': request})
        paginated_response = paginator.get_paginated_response(serializer.data)

        current_subject_total = qs.count() if subject else None

        return self.success_response(
            {
                "history": paginated_response.data,
                "subject_filter": subject,
                "current_subject_total": current_subject_total,
                "subject_summary": subject_summary,
            },
            message="Scan history fetched successfully."
        )






class SaveScanToLibraryView(StandardResponseMixin, APIView):
    pass 


class AiPersonalizationCreateView(StandardResponseMixin, APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        serializer = AiPersonalizationSerializer(data=request.data)
        if not serializer.is_valid():
            reason = extract_first_error(serializer.errors)
            return self.error_response(f"Invalid request: {reason}", status_code=400, data=serializer.errors)

        obj = serializer.save(user=request.user)
        return self.success_response(
            {
                "id": str(obj.id),
                "model": obj.model,
                "response_sytel": obj.response_sytel,
                "dificulty_level": obj.dificulty_level,
                "language": obj.language,
                "subject_focus_area": obj.subject_focus_area,
            },
            message="AI personalization saved successfully.",
            status_code=201,
        )














