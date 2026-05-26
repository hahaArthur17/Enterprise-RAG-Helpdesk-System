using System.Net.Http.Headers;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Microsoft.Extensions.Configuration;

namespace BackendApi.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    [Authorize]
    public class DocumentController : ControllerBase
    {
        private readonly IHttpClientFactory _httpClientFactory;
        private readonly ILogger<DocumentController> _logger;
        private readonly string _pythonServiceUrl;

        public DocumentController(IHttpClientFactory httpClientFactory, ILogger<DocumentController> logger, IConfiguration configuration)
        {
            _httpClientFactory = httpClientFactory;
            _logger = logger;
            _pythonServiceUrl = configuration["PYTHON_SERVICE_URL"]
                                ?? "https://erag-ai-service-ewdsckb4aggbh3ay.australiaeast-01.azurewebsites.net";
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

                var fileStreamContent = new StreamContent(System.IO.File.OpenRead(filePath));
                fileStreamContent.Headers.ContentType = new MediaTypeHeaderValue(file.ContentType);

                multipartFormContent.Add(fileStreamContent, name: "file", fileName: file.FileName);

                _logger.LogInformation("Forwarding file to Python AI service...");
                var pythonResponse = await client.PostAsync($"{_pythonServiceUrl}/upload", multipartFormContent);

                if (!pythonResponse.IsSuccessStatusCode)
                {
                    _logger.LogError("Python service failed to accept the file.");
                    return StatusCode(500, new { error = "AI service failed to accept the document." });
                }

                // 3. Parse the 202 response to get the job ID
                var responseJson = await pythonResponse.Content.ReadAsStringAsync();
                var result = JsonSerializer.Deserialize<JsonElement>(responseJson);
                var jobId = result.GetProperty("job_id").GetString();

                _logger.LogInformation("File accepted by AI service. Job ID: {JobId}", jobId);

                // Return 202 Accepted with the job ID
                return Accepted(new { jobId, message = "File uploaded. Processing in background." });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error occurred during file upload.");
                return StatusCode(500, new { error = "Internal server error during upload." });
            }
        }

        [HttpGet("status/{jobId}")]
        public async Task<IActionResult> GetJobStatus(string jobId)
        {
            try
            {
                var client = _httpClientFactory.CreateClient();
                var response = await client.GetAsync($"{_pythonServiceUrl}/jobs/{jobId}");

                if (response.StatusCode == System.Net.HttpStatusCode.NotFound)
                {
                    return NotFound(new { error = "Job not found." });
                }

                if (!response.IsSuccessStatusCode)
                {
                    _logger.LogError("Failed to get job status from AI service.");
                    return StatusCode(500, new { error = "Failed to get job status." });
                }

                var json = await response.Content.ReadAsStringAsync();
                return Content(json, "application/json");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error fetching job status.");
                return StatusCode(500, new { error = "Internal server error." });
            }
        }
    }
}
