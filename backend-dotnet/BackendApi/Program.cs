using DotNetEnv;

Env.Load(); // Load environment variables from .env file

var builder = WebApplication.CreateBuilder(args);

builder.Configuration.AddEnvironmentVariables();

// --- Add services to the container (Dependency Injection) ---

// Register controllers so the application knows they exist
builder.Services.AddControllers();

// Register IHttpClientFactory so controllers can make external HTTP calls
builder.Services.AddHttpClient();

// Configure CORS (Cross-Origin Resource Sharing) to allow frontend requests
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowFrontend", policy =>
    {
        // Allow the React frontend running on Vite's default port
        policy.WithOrigins("http://localhost:5173")
              .AllowAnyHeader()
              .AllowAnyMethod();
    });
});

var app = builder.Build();

// --- Configure the HTTP request pipeline (Middleware) ---

// Enable the CORS policy defined above
app.UseCors("AllowFrontend");

// Map controller routes to the request pipeline
app.MapControllers();

// Start the application
app.Run();