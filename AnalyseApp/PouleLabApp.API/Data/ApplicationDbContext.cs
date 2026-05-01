using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;
using PouleLabApp.API.Models;

namespace PouleLabApp.API.Data
{
    // Point d'entrée EF Core — relie les modèles C# à la base de données
    public class ApplicationDbContext : IdentityDbContext<ApplicationUser>
    {
        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
            : base(options) { }

        public DbSet<Laboratory> Laboratories => Set<Laboratory>();
        public DbSet<AnalysisRequest> AnalysisRequests => Set<AnalysisRequest>();
        public DbSet<Sample> Samples => Set<Sample>();
        public DbSet<AnalysisType> AnalysisTypes => Set<AnalysisType>();
        public DbSet<AnalysisResult> AnalysisResults => Set<AnalysisResult>();
        public DbSet<Deadline> Deadlines => Set<Deadline>();
        public DbSet<AuditLog> AuditLogs => Set<AuditLog>();
        public DbSet<Notification> Notifications => Set<Notification>();

        protected override void OnModelCreating(ModelBuilder builder)
        {
            base.OnModelCreating(builder);

            // AnalysisRequest → Client (pas de cascade pour éviter les conflits)
            builder.Entity<AnalysisRequest>()
                .HasOne(r => r.Client)
                .WithMany(u => u.SubmittedRequests)
                .HasForeignKey(r => r.ClientId)
                .OnDelete(DeleteBehavior.Restrict);

            // AnalysisRequest → AssignedTo
            builder.Entity<AnalysisRequest>()
                .HasOne(r => r.AssignedTo)
                .WithMany(u => u.AssignedRequests)
                .HasForeignKey(r => r.AssignedToId)
                .OnDelete(DeleteBehavior.Restrict);

            // AnalysisResult → RecordedBy
            builder.Entity<AnalysisResult>()
                .HasOne(r => r.RecordedBy)
                .WithMany()
                .HasForeignKey(r => r.RecordedById)
                .OnDelete(DeleteBehavior.Restrict);

            // AuditLog → PerformedBy
            builder.Entity<AuditLog>()
                .HasOne(a => a.PerformedBy)
                .WithMany()
                .HasForeignKey(a => a.PerformedById)
                .OnDelete(DeleteBehavior.Restrict);

            // Stocker les enums comme strings lisibles en base
            builder.Entity<AnalysisRequest>()
                .Property(r => r.Status)
                .HasConversion<string>();

            builder.Entity<Deadline>()
                .Property(d => d.Phase)
                .HasConversion<string>();
        }
    }
}