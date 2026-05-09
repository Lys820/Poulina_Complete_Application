using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using PouleLabApp.API.Models;

namespace PouleLabApp.API.Data
{
    // Remplit la base de données avec les données initiales indispensables au fonctionnement
    // Appelé une seule fois au démarrage de l'application via Program.cs
    public static class DataSeeder
    {
        public static async Task SeedAsync(
            RoleManager<IdentityRole> roleManager,
            UserManager<ApplicationUser> userManager,
            ApplicationDbContext context)
        {
            // -------------------------------------------------------
            // 1. RÔLES
            // -------------------------------------------------------
            var roles = new[]
            {
                "Administrator", "Manager", "Receptionist",
                "Analyst", "LabChief", "Client"
            };

            foreach (var role in roles)
            {
                if (!await roleManager.RoleExistsAsync(role))
                {
                    await roleManager.CreateAsync(new IdentityRole(role));
                    Console.WriteLine($"[Seeder] Rôle créé : {role}");
                }
            }

            // -------------------------------------------------------
            // 2. COMPTE ADMINISTRATEUR INITIAL
            // -------------------------------------------------------
            const string adminEmail = "admin@poulelabapp.com";
            const string adminPassword = "Admin@1234";

            var existingAdmin = await userManager.FindByEmailAsync(adminEmail);
            if (existingAdmin == null)
            {
                var admin = new ApplicationUser
                {
                    UserName = adminEmail,
                    Email = adminEmail,
                    FirstName = "Super",
                    LastName = "Admin",
                    FilialeName = "Poulina Group Holding",
                    IsActive = true,
                    CreatedAt = DateTime.UtcNow,
                    EmailConfirmed = true
                };

                var result = await userManager.CreateAsync(admin, adminPassword);
                if (result.Succeeded)
                {
                    await userManager.AddToRoleAsync(admin, "Administrator");
                    Console.WriteLine($"[Seeder] Compte admin créé : {adminEmail}");
                }
            }

            // -------------------------------------------------------
            // 3. LABORATOIRES
            // Les 4 laboratoires du groupe Poulina mentionnés dans le cahier des charges
            // -------------------------------------------------------
            if (!await context.Laboratories.AnyAsync())
            {
                var laboratories = new List<Laboratory>
                {
                    new() {
                        Name = "DICK",
                        Description = "Laboratoire vétérinaire et aviculture",
                        Address = "Tunis, Tunisie",
                        TemplateType = FormTemplateType.DICK
                    },
                    new() {
                        Name = "SNA",
                        Description = "Analyses industrielles standard",
                        Address = "Sfax, Tunisie",
                        TemplateType = FormTemplateType.SNA
                    },
                    new() {
                        Name = "GIPA",
                        Description = "Analyses huiles et lubrifiants",
                        Address = "Sousse, Tunisie",
                        TemplateType = FormTemplateType.GIPA
                    },
                    new() {
                        Name = "MEDOIL",
                        Description = "Analyses corps gras et huiles alimentaires",
                        Address = "Bizerte, Tunisie",
                        TemplateType = FormTemplateType.MEDOIL
                    }
                };

                context.Laboratories.AddRange(laboratories);
                await context.SaveChangesAsync();
                Console.WriteLine("[Seeder] Laboratoires créés : DICK, SNA, GIPA, MEDOIL");
            }

            // -------------------------------------------------------
            // 4. TYPES D'ANALYSES
            // Exemples de types d'analyses avec valeurs de référence
            // -------------------------------------------------------
            if (!await context.AnalysisTypes.AnyAsync())
            {
                var analysisTypes = new List<AnalysisType>
                {
                    new() { Name = "pH",              Unit = "pH",    Description = "Mesure de l'acidité",           ReferenceMin = 6.5,  ReferenceMax = 8.5  },
                    new() { Name = "Viscosité",       Unit = "cSt",   Description = "Viscosité cinématique",         ReferenceMin = 28.0, ReferenceMax = 35.0 },
                    new() { Name = "Densité",         Unit = "g/cm³", Description = "Densité à 15°C",               ReferenceMin = 0.85, ReferenceMax = 0.95 },
                    new() { Name = "Indice d'acide",  Unit = "mgKOH", Description = "Indice d'acidité totale",      ReferenceMin = 0.0,  ReferenceMax = 2.5  },
                    new() { Name = "Teneur en eau",   Unit = "%",     Description = "Pourcentage d'eau",            ReferenceMin = 0.0,  ReferenceMax = 0.1  },
                    new() { Name = "Point d'éclair",  Unit = "°C",    Description = "Température d'inflammation",   ReferenceMin = 180,  ReferenceMax = 250  }
                };

                context.AnalysisTypes.AddRange(analysisTypes);
                await context.SaveChangesAsync();
                Console.WriteLine("[Seeder] Types d'analyses créés : pH, Viscosité, Densité...");
            }
        }
    }
}