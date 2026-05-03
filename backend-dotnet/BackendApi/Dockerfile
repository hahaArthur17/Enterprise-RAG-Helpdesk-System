# backend-dotnet/BackendApi/Dockerfile

# Stage 1: Build using the .NET SDK
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

# Copy csproj and restore as distinct layers
COPY ["BackendApi.csproj", "./"]
RUN dotnet restore "./BackendApi.csproj"

# Copy everything else and build
COPY . .
RUN dotnet publish "BackendApi.csproj" -c Release -o /app/publish /p:UseAppHost=false

# Stage 2: Run using the ASP.NET Core Runtime
FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS final
WORKDIR /app

# Copy the published app
COPY --from=build /app/publish .

# Expose standard port 8080 for .NET 8 containers
EXPOSE 8080

ENTRYPOINT ["dotnet", "BackendApi.dll"]