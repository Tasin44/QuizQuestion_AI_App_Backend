from django.shortcuts import render
import os 
import httpx
# Create your views here.
from coreapp.mixins import StandardResponseMixin,extract_first_error
from coreapp.paginations import PageNumberPagination,StandardPagination
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .serializers import SendMessageSerializer,StartChatSerializer,ChatSessionSerializer,ChatMessageSerializer,AskAIMessageSerializer,AskHistorySerializer
from .models import ChatSession,ChatMessage,AskChatHistory
from profileapp.models import UserProfile
from scanapp.views import call_ai   # reuse working scan logic
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

#❓❓❓ why httpx used
def call_chat_ai(subject: str, history: list, user_message: str,model_choice: str) -> str:#❓❓❓ what does they mean: subject:str,history:list,user_message:str
    """
    Sends full conversation history to OpenAI ChatCompletion.
    history = [{"role": "user"/"assistant", "content": "..."}, ...]
    """


    import os,httpx 
 
    if subject:
        system_prompt = (
            f"You are an expert {subject} tutor. "
            f"Analyze the provided image and answer clearly step by step. "
            f"Focus only on {subject}-related content."
        )
    else:
        system_prompt = (
            "You are an intelligent AI tutor. "
            "Analyze the provided image and explain it clearly step by step. "
            "Answer based on any relevant subject."
        )

    #❓❓❓ what does two messages means? why they two used 
    # Build message list: system prompt + full history + new user message
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)                              # past conversation
    messages.append({"role": "user", "content": user_message})  # new message

    #❓❓❓am I passing here request and the ai response fetching 
    # response = httpx.post(
    #     "https://api.openai.com/v1/chat/completions",
    #     headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    #     json={"model": "gpt-4o", "messages": messages, "max_tokens": 1500},
    #     timeout=60.0
    # )
 
    # 🔥 MODEL SWITCHING LOGIC
    if model_choice == "gpt":
        api_key = os.getenv("OPENAI_API_KEY")
        print(f"Open ai api key: {api_key}")

        if not api_key:
            raise ValueError(
                "AI service is not configured. "
                "Please ask the administrator to set OPENAI_API_KEY."
            )
        
        url = "https://api.openai.com/v1/chat/completions"

        response = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o",
                "messages": messages,
                "max_tokens": 1500
            },
            timeout=60.0
        )

        if response.status_code != 200:
            raise ValueError(f"GPT error: {response.text}")

        return response.json()['choices'][0]['message']['content']
    # '''
    # elif model_choice == "claude":
    #     api_key = os.getenv("CLAUDE_API_KEY")
    #     print(f"Claude ai api key: {api_key}")
    #     url = "https://api.anthropic.com/v1/messages"

    #     response = httpx.post(
    #         url,
    #         headers={
    #             "x-api-key": api_key,
    #             "anthropic-version": "2023-06-01",
    #             "Content-Type": "application/json"
    #         },
    #         json={
    #             "model": "claude-3-sonnet-20240229",
    #             "max_tokens": 1500,
    #             "messages": messages
    #         },
    #         timeout=60.0
    #     )

    #     if response.status_code != 200:
    #         raise ValueError(f"Claude error: {response.text}")

    #     return response.json()['content'][0]['text'] ##❓❓❓ explain this line
    # '''
    elif model_choice == "claude":
        api_key = os.getenv("CLAUDE_API_KEY")

        print("===== DEBUG CLAUDE =====")
        print("CLAUDE KEY:", api_key)
        print("TYPE:", type(api_key))
        print("========================")
        if not api_key:
            raise ValueError(
                "AI service is not configured. "
                "Please ask the administrator to set CLAUDE_API_KEY."
            )

        url = "https://api.anthropic.com/v1/messages"

        # Claude requires system separately
        claude_messages = []

        for msg in history:
            if msg["role"] in ["user", "assistant"]:
                claude_messages.append({
                    "role": msg["role"],
                    "content": [{"type": "text", "text": msg["content"]}]
                })

        # add latest user message
        claude_messages.append({
            "role": "user",
            #"content": user_message
            "content": [{"type": "text", "text": user_message}]
        })

        response = httpx.post(
            url,
            headers={
                "x-api-key": api_key,
                # "anthropic-version": "2023-06-01",
                #"anthropic-version": "2024-06-01",
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json={
                # "model": "claude-3-haiku-20240307",
                #"model": "claude-3-5-sonnet-latest",
                # "model": "claude-3-haiku-latest",
                # "model": "claude-3-sonnet-20240229",
                # "model": "claude-3-haiku-20240307",
                # "model": "claude-3-5-haiku-latest",
                # "model":"claude-3-5-haiku-20241022",
                # "model": "claude-2.1",
                "model": "claude-sonnet-4-5-20250929",
                "max_tokens": 1500,
                "system": system_prompt,
                "messages": claude_messages
            },
            timeout=60.0
        )

        if response.status_code != 200:
            raise ValueError(f"Claude error: {response.text}")

        return response.json()["content"][0]["text"]
    elif model_choice == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        print(f"Gemini api key: {api_key}")

        if not api_key:
            raise ValueError(
                "AI service is not configured. "
                "Please ask the administrator to set GEMINI_API_KEY."
            )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

        # Build conversation for Gemini
        conversation_text = ""

        if subject:
            conversation_text += f"System Instruction: {system_prompt}\n\n"
        else:
            conversation_text += f"{system_prompt}\n\n"

        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            conversation_text += f"{role}: {msg['content']}\n"

        conversation_text += f"User: {user_message}"

        response = httpx.post(
            url,
            headers={
                "Content-Type": "application/json"
            },
            json={
                "contents": [
                    {
                        "parts": [
                            {"text": conversation_text}
                        ]
                    }
                ]
            },
            timeout=60.0
        )

        if response.status_code != 200:
            raise ValueError(f"Gemini error: {response.text}")

        return response.json()["candidates"][0]["content"]["parts"][0]["text"]

    else:
        raise ValueError("Invalid AI model selected")
 
 
 

#❓❓❓what if I wants to use every modelname.objects.create() get_or_create instead

#❓❓❓why not I'm using just startchatserializer why not chatsession serialiser also?


class StartChatView(StandardResponseMixin, APIView):
    """
    POST /chat/start/
    Creates a new chat session for a subject.
    """
    permission_classes = [IsAuthenticated]
 
    def post(self, request):
        serializer = StartChatSerializer(data=request.data)
        if not serializer.is_valid():
            reason = extract_first_error(serializer.errors)
            return self.error_response(f"Could not start chat: {reason}", status_code=400)
 
        session = ChatSession.objects.create(
            user=request.user,
            subject=serializer.validated_data['subject'],
            title=serializer.validated_data.get('title', '').strip() or 'New Chat'
        )
        return self.success_response(
            ChatSessionSerializer(session).data,#❓❓❓ why I'm not using serializer.data? is it because I'll be only able to use serailzier.data when we use the same serializer at the top of the method and expect response from that ?
            message="Chat session started. You can now send messages.",
            status_code=201
        )



class SendMessageView(StandardResponseMixin, APIView):
    """
    POST /chat/<session_id>/message/
    Send a message, get AI reply. Full history is sent to AI each time.
    """
    permission_classes = [IsAuthenticated]
 
    def post(self, request, session_id):
        # Verify session ownership — users cannot access other users' chats
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)#❓❓❓ why not filter,why .get?
            #❓❓❓ why chatsession checking is necessary in this view?
        except ChatSession.DoesNotExist:#❓❓❓ may I use here session.doesnotexist or just except?
            return self.error_response(
                "Chat session not found or you do not have permission to access it.",
                status_code=404
            )
 
        serializer = SendMessageSerializer(data=request.data)
        if not serializer.is_valid():
            reason = extract_first_error(serializer.errors)
            return self.error_response(f"Message invalid: {reason}", status_code=400)
 
        user_text = serializer.validated_data['message']
        model_choice = serializer.validated_data.get('model', 'gpt')  
        # Fetch last 20 messages for context (prevents huge payloads to AI)
        # Only fetch role + content — we don't need id/created_at for the AI call
        past_messages = list(# #❓❓❓why this list() used? 
            session.messages# ChatMessage model 'session' field related name
            .values('role', 'content')
            .order_by('created_at')[:20]         # oldest first, limit 20
        )
 
        # Call AI with history
        try:
            ai_reply = call_chat_ai(session.subject, past_messages, user_text,model_choice)
        except ValueError as e:
            return self.error_response(str(e), status_code=503)
        except Exception as e:
            print("ERROR:", str(e)) 
            return self.error_response(
                "AI service is temporarily unavailable. Please try again shortly.",
                status_code=503
            )
 
        # Save both messages in bulk to minimize DB round trips
        #❓❓❓ why this bulk creation doing here
        #❓❓❓this 3(session,role,content) is the mandatory field
        ChatMessage.objects.bulk_create([
            ChatMessage(session=session, role=ChatMessage.ROLE_USER, content=user_text),
            ChatMessage(session=session, role=ChatMessage.ROLE_AI, content=ai_reply),
        ])
 
        # Update session timestamp so ordering works correctly
        session.save(update_fields=['updated_at'])
 
        # Increment problems_solved counter
        from django.db.models import F
        UserProfile.objects.filter(user=request.user).update(
            problems_solved=F('problems_solved') + 1
        )
 
        return self.success_response(
            {"role": "assistant", "content": ai_reply},
            message="Message sent and AI response received.",
            status_code=200
        )
        


        




class ChatHistoryView(StandardResponseMixin,APIView):

    permission_classes=[IsAuthenticated]

    def get(self,requst,session_id):
        try:
            session = ChatSession.objects.get(id=session_id,user=self.request.user)
        except ChatSession.DoesNotExist:
            return self.error_response(
                "Chat session not found",
                status_code=404
            )
        
        
        messages=session.messages.all()#chatmessage model connected with chatsession model with the related name messages that why this  messages used right?
        paginator=StandardPagination()


class ChatHistoryView(StandardResponseMixin, APIView):
    """
    GET /chat/<session_id>/messages/
    Returns paginated message history for a session.
    """
    permission_classes = [IsAuthenticated]
 
    def get(self, request, session_id):
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            return self.error_response(
                "Chat session not found or access denied.",
                status_code=404
            )
        
        #❓❓❓ what if I want to write the serializer line here serializer = ChatMessageSerializer(page, many=True)
        #❓❓❓how to know I should use this below 4 field here, messages,paginator,page,
        messages = session.messages.all()#chatmessage model connected with chatsession model with the related name messages that why this  messages used right?
        paginator = StandardPagination()
        page = paginator.paginate_queryset(messages, request)
        serializer = ChatMessageSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
 


class ChatSessionListView(StandardResponseMixin, APIView):
    """
    GET /chat/sessions/?subject=math
    Lists all chat sessions for the logged-in user.
    """
    permission_classes = [IsAuthenticated]
 
    def get(self, request):
        qs = ChatSession.objects.filter(user=request.user)#❓❓❓ what is qs here?
        subject = request.query_params.get('subject')
        if subject:
            qs = qs.filter(subject=subject)
 
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ChatSessionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)





class AskAPIView(StandardResponseMixin, APIView):
    """
    POST /chat/ask/   -> ask + save prompt/response (message/model optional, supports image/file)
    GET  /chat/ask/   -> list all ask history of logged in user
    DELETE /chat/ask/ -> delete all ask history of logged in user
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # support file uploads

    def post(self, request):
        serializer = AskAIMessageSerializer(data=request.data)

        if not serializer.is_valid():
            reason = extract_first_error(serializer.errors)
            return self.error_response(f"Invalid request: {reason}", status_code=400)

        user_text = serializer.validated_data.get('message', '').strip()
        subject = serializer.validated_data.get('subject', None)
        model_choice = serializer.validated_data.get('model', 'gpt')   # default GPT
        image = serializer.validated_data.get('image')
        file = serializer.validated_data.get('file')

        ai_reply = None

        # If image or file provided — use call_ai() from scanapp (already working)
        if image or file:
            uploaded_file = image or file
            question = user_text or f"Explain this {subject or 'content'}."
            try:
                ai_reply = call_ai(
                    uploaded_file,
                    subject or 'general',
                    question,
                    model="gpt-4o"   # call_ai uses OpenAI vision; model_choice for text handled below
                )
            except ValueError as e:
                return self.error_response(str(e), status_code=503)
            except Exception as e:
                print("ERROR:", str(e))
                return self.error_response("AI service unavailable", status_code=503)

        # If only text — use call_chat_ai() as before
        else:
            history = []
            try:
                ai_reply = call_chat_ai(subject, history, user_text, model_choice)
            except Exception as e:
                print("ERROR:", str(e))
                return self.error_response("AI service unavailable", status_code=503)

        AskChatHistory.objects.create(
            user=request.user,
            prompt=user_text,
            ai_response=ai_reply,
            image=image if image else None,
            file=file if file else None,
        )

        return self.success_response(
            {"role": "assistant", "content": ai_reply},
            message="AI response generated",
            status_code=200
        )

    def get(self, request):
        qs = AskChatHistory.objects.filter(user=request.user)
        serializer = AskHistorySerializer(qs, many=True, context={'request': request})  # ADD context
        return self.success_response(serializer.data, message="Ask history fetched.")

    def delete(self, request):
        deleted_count, _ = AskChatHistory.objects.filter(user=request.user).delete()
        return self.success_response(
            {"deleted_count": deleted_count},
            message="All ask history deleted successfully."
        )
















