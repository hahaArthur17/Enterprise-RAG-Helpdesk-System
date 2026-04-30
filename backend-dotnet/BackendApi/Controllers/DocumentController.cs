using System.Net.Http.Headers;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;

namespace BackendApi.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    [Authorize]
    public class DocumentController : ControllerBase
    {
        private readonly IHttpClientFactory _httpClientFactory;
        private readonly ILogger<DocumentController> _logger;

        public DocumentController(IHttpClientFactory httpClientFactory, ILogger<DocumentController> logger)
        {
            _httpClientFactory = httpClientFactory;
            _logger = logger;
        }

        [HttpPost("upload")]
        public async Task<IActionResult> UploadDocument(IFormFile file)
        {
            if (file == null || file.Length == 0)
            {
                return BadRequest(new { error = "No file uploaded." });
            }

            try
            {
                // 1. Save the file locally
                var uploadsFolder = Path.Combine(Directory.GetCurrentDirectory(), "Uploads");
                if (!Directory.Exists(uploadsFolder))
                {
                    Directory.CreateDirectory(uploadsFolder);
                }

                var filePath = Path.Combine(uploadsFolder, file.FileName);
                using (var stream = new FileStream(filePath, FileMode.Create))
                {
                    await file.CopyToAsync(stream);
                }
                _logger.LogInformation("File {FileName} saved locally at {Path}", file.FileName, filePath);

                // 2. Forward the file to the Python AI service
                var client = _httpClientFactory.CreateClient();
                using var multipartFormContent = new MultipartFormDataContent();
                
                // Read the saved file into memory for forwarding
                var fileStreamContent = new StreamContent(System.IO.File.OpenRead(filePath));
                fileStreamContent.Headers.ContentType = new MediaTypeHeaderValue(file.ContentType);
                
                // "file" is the parameter name expected by FastAPI
                multipartFormContent.Add(fileStreamContent, name: "file", fileName: file.FileName);

                _logger.LogInformation("Forwarding file to Python AI service...");
                var pythonResponse = await client.PostAsync("http://localhost:8000/upload", multipartFormContent);

                if (!pythonResponse.IsSuccessStatusCode)
                {
                    _logger.LogError("Python service failed to process the file.");
                    return StatusCode(500, new { error = "AI service failed to process the document." });
                }

                _logger.LogInformation("File successfully processed by AI service.");
                return Ok(new { message = "Document uploaded and embedded successfully." });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error occurred during file upload.");
                return StatusCode(500, new { error = "Internal server error during upload." });
            }
        }
    }
}