from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


MAX_MESSAGES = 12
MAX_MESSAGE_LENGTH = 1600
MAX_TOTAL_LENGTH = 8000


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[ChatMessage] = Field(min_length=1, max_length=MAX_MESSAGES)

    @model_validator(mode="after")
    def validate_conversation(self):
        if self.messages[-1].role != "user":
            raise ValueError("The last message must be from the user.")
        if self.messages[0].role != "user":
            raise ValueError("The first message must be from the user.")
        if any(
            current.role == previous.role
            for previous, current in zip(self.messages, self.messages[1:])
        ):
            raise ValueError("Conversation roles must alternate.")
        if sum(len(message.content) for message in self.messages) > MAX_TOTAL_LENGTH:
            raise ValueError("The conversation is too long.")
        if any(not message.content.strip() for message in self.messages):
            raise ValueError("Messages must not be blank.")
        return self


class ChatResponse(BaseModel):
    reply: str
