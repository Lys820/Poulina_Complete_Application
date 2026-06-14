USE PouleLabDB;

DELETE FROM AuditLogs;
DELETE FROM Notifications;
DELETE FROM Deadlines;
DELETE FROM AnalysisResults;
DELETE FROM Samples;
DELETE FROM AnalysisRequests;

DBCC CHECKIDENT ('AuditLogs', RESEED, 0);
DBCC CHECKIDENT ('Notifications', RESEED, 0);
DBCC CHECKIDENT ('Deadlines', RESEED, 0);
DBCC CHECKIDENT ('AnalysisResults', RESEED, 0);
DBCC CHECKIDENT ('Samples', RESEED, 0);
DBCC CHECKIDENT ('AnalysisRequests', RESEED, 0);