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
            if (!context.Laboratories.Any())
            {
                context.Laboratories.AddRange(
                    // Labos DICK — Laboratoire vétérinaire
                    new Laboratory {
                        Name         = "BioVet Analyses",
                        Description  = "Laboratoire d'analyses vétérinaires DICK",
                        Address      = "Zone Industrielle, Tunis",
                        TemplateType = FormTemplateType.DICK
                    },
                    new Laboratory {
                        Name         = "LabAnimal Control",
                        Description  = "Contrôle sanitaire élevage DICK",
                        Address      = "Route de Bizerte, Mateur",
                        TemplateType = FormTemplateType.DICK
                    },

                    // Labos SNA — Analyses industrielles
                    new Laboratory {
                        Name         = "IndustriaLab SNA",
                        Description  = "Laboratoire d'analyses industrielles SNA",
                        Address      = "Zone Industrielle, Sfax",
                        TemplateType = FormTemplateType.SNA
                    },
                    new Laboratory {
                        Name         = "TechnoAnalyse SNA",
                        Description  = "Contrôle qualité huiles industrielles",
                        Address      = "Route de Gabes, Sfax",
                        TemplateType = FormTemplateType.SNA
                    },

                    // Labos GIPA — Huiles & Lubrifiants
                    new Laboratory {
                        Name         = "LubroLab GIPA",
                        Description  = "Analyses huiles et lubrifiants GIPA",
                        Address      = "Zone Industrielle, Sousse",
                        TemplateType = FormTemplateType.GIPA
                    },
                    new Laboratory {
                        Name         = "OilControl GIPA",
                        Description  = "Contrôle qualité lubrifiants",
                        Address      = "Boulevard de l'environnement, Sousse",
                        TemplateType = FormTemplateType.GIPA
                    },

                    // Labos MEDOIL — Corps gras
                    new Laboratory {
                        Name         = "AlimentaLab MEDOIL",
                        Description  = "Analyses corps gras et huiles alimentaires",
                        Address      = "Zone Industrielle, Bizerte",
                        TemplateType = FormTemplateType.MEDOIL
                    },
                    new Laboratory {
                        Name         = "FoodQuality MEDOIL",
                        Description  = "Contrôle qualité huiles alimentaires",
                        Address      = "Route de Tunis, Bizerte",
                        TemplateType = FormTemplateType.MEDOIL
                    }
                );
                await context.SaveChangesAsync();
            }
                Console.WriteLine("[Seeder] Laboratoires créés : DICK, SNA, GIPA, MEDOIL");
            }
        }
    }
