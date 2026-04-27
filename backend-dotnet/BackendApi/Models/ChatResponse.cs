namespace BackendApi.Models
{
    // Represents the structure of a chat message, matching frontend's Message interface
    public class ChatResponse
    {
        public string Id { get; set; } = string.Empty;
        public string Role { get; set; } = string.Empty;
        public string Content { get; set; } = string.Empty;
    }
}