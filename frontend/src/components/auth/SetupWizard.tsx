"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { setToken } from "@/lib/auth";
import { InviteForm } from "./InviteForm";

const STEPS = [
  "Create Admin Account",
  "Verify Email",
  "Organization Name",
  "SMTP Configuration",
  "Invite Team",
  "Confirmation",
];

interface SetupWizardProps {
  onComplete: () => void;
}

export function SetupWizard({ onComplete }: SetupWizardProps) {
  const [step, setStep] = useState(0);
  const [error, setError] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [name, setName] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [fallbackCode, setFallbackCode] = useState("");
  const [orgName, setOrgName] = useState("");
  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState("587");
  const [smtpUsername, setSmtpUsername] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [smtpFrom, setSmtpFrom] = useState("");

  const handleCreateAdmin = async () => {
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    setError("");
    try {
      const response = await api.post<{
        access_token: string;
        email_sent: boolean;
        verification_code?: string;
      }>("/api/bootstrap/create-admin", { email, password, name: name || undefined });
      setToken(response.access_token);
      if (response.verification_code) {
        setFallbackCode(response.verification_code);
      }
      setStep(1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create admin");
    }
  };

  const handleVerifyEmail = async () => {
    setError("");
    try {
      await api.post("/api/auth/verify-email", { email, code: verificationCode });
      setStep(2);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Verification failed");
    }
  };

  const handleConfigureOrg = async () => {
    setError("");
    try {
      await api.post("/api/bootstrap/configure-org", { org_name: orgName });
      setStep(3);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to configure org");
    }
  };

  const handleConfigureSmtp = async () => {
    setError("");
    try {
      await api.post("/api/bootstrap/configure-smtp", {
        host: smtpHost,
        port: parseInt(smtpPort),
        username: smtpUsername,
        password: smtpPassword,
        from_address: smtpFrom,
      });
      setStep(4);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to configure SMTP");
    }
  };

  const handleComplete = async () => {
    try {
      await api.post("/api/bootstrap/complete");
      onComplete();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to complete setup");
    }
  };

  return (
    <div className="bg-white shadow rounded-lg p-8">
      {/* Step indicator */}
      <div className="flex items-center justify-between mb-8">
        {STEPS.map((label, i) => (
          <div key={label} className="flex items-center">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                i === step
                  ? "bg-bioaf-600 text-white"
                  : i < step
                    ? "bg-green-500 text-white"
                    : "bg-gray-200 text-gray-500"
              }`}
            >
              {i < step ? "\u2713" : i + 1}
            </div>
            {i < STEPS.length - 1 && (
              <div className={`w-8 h-0.5 ${i < step ? "bg-green-500" : "bg-gray-200"}`} />
            )}
          </div>
        ))}
      </div>

      <h2 className="text-xl font-semibold mb-4">{STEPS[step]}</h2>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">
          {error}
        </div>
      )}

      {/* Step 1: Create Admin */}
      {step === 0 && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-bioaf-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-bioaf-500" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-bioaf-500" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Confirm Password</label>
            <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-bioaf-500" required />
          </div>
          <button onClick={handleCreateAdmin} className="w-full bg-bioaf-600 text-white py-2 rounded hover:bg-bioaf-700">
            Create Admin Account
          </button>
        </div>
      )}

      {/* Step 2: Verify Email */}
      {step === 1 && (
        <div className="space-y-4">
          {fallbackCode && (
            <div className="p-3 bg-yellow-50 border border-yellow-200 text-yellow-800 rounded text-sm">
              SMTP not configured. Your verification code is: <strong>{fallbackCode}</strong>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Verification Code</label>
            <input type="text" value={verificationCode} onChange={(e) => setVerificationCode(e.target.value)}
              placeholder="Enter 6-digit code"
              className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-bioaf-500" />
          </div>
          <button onClick={handleVerifyEmail} className="w-full bg-bioaf-600 text-white py-2 rounded hover:bg-bioaf-700">
            Verify Email
          </button>
          <button onClick={() => setStep(2)} className="w-full text-gray-500 text-sm hover:text-gray-700">
            Skip for now
          </button>
        </div>
      )}

      {/* Step 3: Org Name */}
      {step === 2 && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Organization Name</label>
            <input type="text" value={orgName} onChange={(e) => setOrgName(e.target.value)}
              placeholder="e.g., Acme Biotech"
              className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-bioaf-500" required />
          </div>
          <button onClick={handleConfigureOrg} className="w-full bg-bioaf-600 text-white py-2 rounded hover:bg-bioaf-700">
            Save Organization Name
          </button>
        </div>
      )}

      {/* Step 4: SMTP */}
      {step === 3 && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">SMTP Host</label>
              <input type="text" value={smtpHost} onChange={(e) => setSmtpHost(e.target.value)}
                className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-bioaf-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
              <input type="number" value={smtpPort} onChange={(e) => setSmtpPort(e.target.value)}
                className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-bioaf-500" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
            <input type="text" value={smtpUsername} onChange={(e) => setSmtpUsername(e.target.value)}
              className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-bioaf-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input type="password" value={smtpPassword} onChange={(e) => setSmtpPassword(e.target.value)}
              className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-bioaf-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">From Address</label>
            <input type="email" value={smtpFrom} onChange={(e) => setSmtpFrom(e.target.value)}
              className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-bioaf-500" />
          </div>
          <button onClick={handleConfigureSmtp} className="w-full bg-bioaf-600 text-white py-2 rounded hover:bg-bioaf-700">
            Save SMTP Configuration
          </button>
          <button onClick={() => setStep(4)} className="w-full text-gray-500 text-sm hover:text-gray-700">
            Skip for now
          </button>
        </div>
      )}

      {/* Step 5: Invite Team */}
      {step === 4 && (
        <div className="space-y-4">
          <InviteForm />
          <button onClick={() => setStep(5)} className="w-full bg-bioaf-600 text-white py-2 rounded hover:bg-bioaf-700">
            Continue
          </button>
          <button onClick={() => setStep(5)} className="w-full text-gray-500 text-sm hover:text-gray-700">
            Skip for now
          </button>
        </div>
      )}

      {/* Step 6: Confirmation */}
      {step === 5 && (
        <div className="space-y-4">
          <div className="p-4 bg-green-50 border border-green-200 rounded">
            <h3 className="font-semibold text-green-800">Setup Summary</h3>
            <ul className="mt-2 text-sm text-green-700 space-y-1">
              <li>Admin account created</li>
              {orgName && <li>Organization: {orgName}</li>}
              <li>Platform ready to use</li>
            </ul>
          </div>
          <button onClick={handleComplete} className="w-full bg-bioaf-600 text-white py-2 rounded hover:bg-bioaf-700">
            Launch bioAF
          </button>
        </div>
      )}
    </div>
  );
}
