namespace BackendApi.Models
{
    // Represents the incoming request payload from the frontend
    public class ChatRequest
    {
        public string Message { get; set; } = string.Empty;
    }
}