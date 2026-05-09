using System.Text;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using PouleLabApp.API.Data;
using PouleLabApp.API.Models;
using PouleLabApp.API.Services;
using PouleLabApp.API.Services.Interfaces;
using Scalar.AspNetCore;
using PouleLabApp.API.Middleware;


var builder = WebApplication.CreateBuilder(args);

// ============================================================
// 1. BASE DE DONNÉES
// La chaîne de connexion vient des User Secrets (jamais en dur)
// ============================================================
builder.Services.AddDbContext<ApplicationDbContext>(options =>
    options.UseSqlServer(builder.Configuration.GetConnectionString("Default")));

// ============================================================
// 2. ASP.NET CORE IDENTITY
// Gère les utilisateurs, mots de passe hashés et rôles
// ============================================================
builder.Services.AddIdentity<ApplicationUser, IdentityRole>(options =>
{
    // Règles de complexité du mot de passe
    options.Password.RequireDigit = true;           // Au moins un chiffre
    options.Password.RequiredLength = 8;            // Minimum 8 caractères
    options.Password.RequireUppercase = true;       // Au moins une majuscule
    options.Password.RequireNonAlphanumeric = false;// Caractères spéciaux non obligatoires

    // Un email unique par compte
    options.User.RequireUniqueEmail = true;
})
.AddEntityFrameworkStores<ApplicationDbContext>() // Stocke les utilisateurs en base via EF Core
.AddDefaultTokenProviders();                       // Active les tokens pour reset de mot de passe etc.

// ============================================================
// 3. JWT AUTHENTICATION
// Valide le token JWT envoyé dans chaque requête protégée
// ============================================================
var jwtSecret = builder.Configuration["Jwt:Secret"]
    ?? throw new InvalidOperationException("Jwt:Secret est manquant dans la configuration.");

builder.Services.AddAuthentication(options =>
{
    // JWT est le schéma d'authentification par défaut
    options.DefaultAuthenticateScheme = JwtBearerDefaults.AuthenticationScheme;
    options.DefaultChallengeScheme = JwtBearerDefaults.AuthenticationScheme;
})
.AddJwtBearer(options =>
{
    options.TokenValidationParameters = new TokenValidationParameters
    {
        ValidateIssuer = true,           // Vérifie que le token vient bien de notre API
        ValidateAudience = true,         // Vérifie que le token est destiné à notre API
        ValidateLifetime = true,         // Vérifie que le token n'est pas expiré
        ValidateIssuerSigningKey = true, // Vérifie la signature cryptographique
        ValidIssuer = builder.Configuration["Jwt:Issuer"],
        ValidAudience = builder.Configuration["Jwt:Audience"],
        IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtSecret)),
        ClockSkew = TimeSpan.Zero        // Pas de tolérance sur l'expiration (plus sécurisé)
    };
});

// ============================================================
// 4. AUTORISATION
// Les policies permettent de protéger les endpoints par rôle
// ============================================================
builder.Services.AddAuthorization(options =>
{
    // Policies strictes — Admin n'a PAS accès au workflow métier
    options.AddPolicy("RequireReceptionistOnly", policy => policy.RequireRole("Receptionist"));
    options.AddPolicy("RequireAnalystOnly",      policy => policy.RequireRole("Analyst"));
    options.AddPolicy("RequireLabChiefOnly",     policy => policy.RequireRole("LabChief"));

    // Policies admin — gestion des utilisateurs uniquement
    options.AddPolicy("RequireAdmin",        policy => policy.RequireRole("Administrator"));
    options.AddPolicy("RequireManager",      policy => policy.RequireRole("Administrator", "Manager"));

    // Historique accessible uniquement à l'Admin et au Chef de labo
    options.AddPolicy("RequireAdminOrLabChief", policy => policy.RequireRole("Administrator", "LabChief"));

    // Création de demande — Client, Manager, Admin uniquement
    options.AddPolicy("RequireClientRole", policy => policy.RequireRole("Administrator", "Manager", "Client"));
});

// ============================================================
// 5. CORS
// Autorise Angular (localhost:4200) à appeler notre API pendant le développement
// ============================================================
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAngular", policy =>
    {
        policy.WithOrigins("http://localhost:4200")
              .AllowAnyHeader()  // Autorise tous les en-têtes HTTP (dont Authorization)
              .AllowAnyMethod(); // Autorise GET, POST, PUT, DELETE etc.
    });
});

// ============================================================
// 6. SERVICES MÉTIER
// Injection de dépendances — on déclare ici tous nos services
// ============================================================
builder.Services.AddScoped<IJwtTokenService, JwtTokenService>();
builder.Services.AddScoped<IAnalysisRequestService, AnalysisRequestService>();
builder.Services.AddScoped<IAuditLogService, AuditLogService>();
// Background service — vérifie les échéances dépassées toutes les heures
builder.Services.AddHostedService<DeadlineCheckerService>();
builder.Services.AddScoped<IEmailService, EmailService>();
// D'autres services seront ajoutés ici au fil des semaines

// ============================================================
// 7. CONTROLLERS + DOCUMENTATION API
// ============================================================
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddOpenApi();

// ============================================================
// CONSTRUCTION DE L'APPLICATION
// ============================================================
var app = builder.Build();
// Doit être le premier middleware pour intercepter toutes les erreurs
app.UseMiddleware<GlobalExceptionHandler>();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
    app.MapScalarApiReference(); // Interface de test de l'API sur /scalar
}

// Redirection HTTPS désactivée en développement pour éviter les conflits de port
// À réactiver en production avec un vrai certificat SSL
if (!app.Environment.IsDevelopment())
{
    app.UseHttpsRedirection();
}
app.UseCors("AllowAngular");  // CORS doit être avant Authentication et Authorization
app.UseAuthentication();      // Vérifie le token JWT sur chaque requête
app.UseAuthorization();       // Vérifie les droits après l'authentification
app.MapControllers();

// ============================================================
// SEEDING — Initialisation des données au démarrage
// S'exécute uniquement si les données n'existent pas encore
// ============================================================
// Après
using (var scope = app.Services.CreateScope())
{
    var roleManager = scope.ServiceProvider.GetRequiredService<RoleManager<IdentityRole>>();
    var userManager = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
    var context = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
    await DataSeeder.SeedAsync(roleManager, userManager, context);
}


app.Run();