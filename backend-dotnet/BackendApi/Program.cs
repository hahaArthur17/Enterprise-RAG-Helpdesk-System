using DotNetEnv;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;
using System.Text;

// 1. Load environment variables from .env file FIRST
Env.Load();

var builder = WebApplication.CreateBuilder(args);
// Connect to Azure Application Insights for telemetry monitoring
builder.Services.AddApplicationInsightsTelemetry();

// 2. Instruct .NET to read configurations from environment variables
builder.Configuration.AddEnvironmentVariables();

// --- Add services to the container (Dependency Injection) ---

builder.Services.AddControllers();
builder.Services.AddHttpClient();

// 3. Configure CORS (Cross-Origin Resource Sharing)
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowFrontend", policy =>
    {
        // Allow the React frontend to communicate with this API
        policy.WithOrigins("http://localhost:5173")
              .AllowAnyHeader()
              .AllowAnyMethod();
    });
});

// 4. Configure JWT Authentication [DAY 14]
// Safely retrieve the secret key from the .env file
var jwtSecretKey = builder.Configuration["JWT_SECRET_KEY"] 
                   ?? throw new InvalidOperationException("JWT Secret Key is missing in .env file.");

builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = builder.Configuration["Jwt:Issuer"], // From appsettings.json
            ValidAudience = builder.Configuration["Jwt:Audience"], // From appsettings.json
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtSecretKey))
        };
    });

var app = builder.Build();

// --- Configure the HTTP request pipeline (Middleware) ---

// 5. Enable CORS (Must be placed before Auth)
app.UseCors("AllowFrontend");

// 6. Enable Authentication & Authorization (Order is critical!)
app.UseAuthentication(); // "Who are you?"
app.UseAuthorization();  // "Are you allowed to be here?"

app.MapControllers();

app.Run();