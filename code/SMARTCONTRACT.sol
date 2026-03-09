// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * BCA — BRICS Clearing Asset
 * Arquitetura Monetária Elástica para Liquidação Intra-Bloco
 * Autor: Armando Freire (armanfm@github.com)
 * Versão: Protótipo TRL-3 — Ethereum Sepolia Testnet
 *
 * Baseado em: "Arquitetura Monetária Elástica para o BRICS" (Março 2026)
 * Parâmetros: λ=0.5, δ=2%, τ=2%, CAP=5%, BURN_CAP=2.5%
 *
 * AVISO: Este é um protótipo de demonstração. Não deploy em produção
 * sem auditoria de segurança profissional.
 */

interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
}

contract BCAToken is IERC20 {

    // =========================================================
    // ESTRUTURAS E EVENTOS
    // =========================================================

    struct Member {
        string  name;           // Nome do membro (ex: "Brasil")
        string  code;           // Código ISO (ex: "BR")
        uint256 gdpWeight;      // Peso λ em basis points (10000 = 100%)
        uint256 miniPIB;        // Volume acumulado de clearing on-chain
        address bcAddress;      // Endereço do Banco Central membro
        bool    active;
    }

    struct ClearingTx {
        address from;
        address to;
        uint256 amount;
        uint256 feeCollected;
        uint256 timestamp;
        string  fromMember;
        string  toMember;
    }

    // Eventos principais
    event ClearingSettled(
        address indexed from,
        address indexed to,
        uint256 amount,
        uint256 fee,
        string fromMember,
        string toMember,
        uint256 timestamp
    );
    event FundamentalUpdated(uint256 newFt, uint256 timestamp);
    event MintExecuted(string regime, uint256 amount, uint256 newSupply);
    event BurnExecuted(uint256 amount, uint256 newSupply);
    event CorridorIntervention(string side, uint256 price, uint256 ft, uint256 amount);
    event MemberAdded(string code, uint256 gdpWeight);
    event GovernanceFundsReceived(string reason, uint256 amount, uint256 timestamp);
    event GovernanceAddressUpdated(address newAddress);

    // =========================================================
    // PARÂMETROS DO PROTOCOLO (conforme paper)
    // =========================================================

    string  public constant NAME     = "BRICS Clearing Asset";
    string  public constant SYMBOL   = "BCA";
    uint8   public constant DECIMALS = 18;

    // Parâmetros calibrados — λ=0.5 recomendado pelo paper (Seção 4)
    uint256 public constant LAMBDA_BPS      = 5000;  // λ=0.5 em basis points de 10000
    uint256 public constant DELTA_BPS       = 200;   // δ=2% corredor bid/ask (Seção 6.4)
    uint256 public constant TAU_BPS         = 200;   // τ=2% taxa de protocolo (Seção 5.3)
    uint256 public constant CAP_BPS         = 500;   // CAP=5% mint máximo/mês (Seção 5.2)
    uint256 public constant BURN_CAP_BPS    = 250;   // BURN_CAP=CAP/2=2.5% (Seção 5.2)
    uint256 public constant MINT_FRACTION   = 1000;  // 10% do incremento mini-PIB (Apêndice A.4)
    uint256 public constant CRISIS_SIGMA    = 200;   // -2σ threshold para burn (Seção 5.2)

    uint256 public constant BPS_BASE        = 10000;
    uint256 public constant PRECISION       = 1e18;

    // =========================================================
    // STATE — SUPPLY E FUNDAMENTAL
    // =========================================================

    uint256 private _totalSupply;
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;

    // F_t — fundamental macroeconômico (Seção 3.1)
    // Representado como inteiro × PRECISION para evitar floats
    uint256 public Ft;                    // Preço fundamental atual
    uint256 public FtPrevious;            // F_t do período anterior
    uint256 public FtAtGenesis;           // F_0 imutável pós-genesis

    // Reserva de taxas R_t (Seção 5.3)
    uint256 public protocolReserve;

    // Mini-PIB acumulado do bloco (Apêndice A.4)
    uint256 public totalMiniPIB;
    uint256 public miniPIBHighWaterMark;  // Máxima histórica

    // Tracking de supply para mint/burn
    uint256 public genesisSupply;
    uint256 public lastMintTimestamp;
    uint256 public lastFtUpdate;

    // =========================================================
    // GOVERNANÇA
    // =========================================================

    address public immutable genesisDeployer;

    // Endereço da governança do bloco BRICS
    // Recebe: τ de cada clearing + ETH das vendas do corredor
    // A governança administra e distribui conforme necessidade do bloco
    address public governanceAddress;

    bool    public genesisComplete;
    bool    public secondaryMarketOpen;
    uint256 public genesisTimestamp;

    // Membros (5 BRICS originais)
    mapping(string => Member) public members;
    string[] public memberCodes;
    uint256  public memberCount;

    // Histórico de transações
    ClearingTx[] public clearingHistory;

    // Pesos λ são estáticos após genesis — imutáveis no contrato
    // Recálculo off-chain: qualquer um pode pegar mini-PIB público e recalcular

    // =========================================================
    // MODIFIERS
    // =========================================================

    modifier onlyGenesis() {
        require(!genesisComplete, "BCA: genesis already complete");
        _;
    }

    modifier onlyMemberBC() {
        bool isMember = false;
        for (uint i = 0; i < memberCodes.length; i++) {
            if (members[memberCodes[i]].bcAddress == msg.sender &&
                members[memberCodes[i]].active) {
                isMember = true;
                break;
            }
        }
        require(isMember, "BCA: caller is not an active member BC");
        _;
    }

    modifier marketOpen() {
        require(secondaryMarketOpen ||
                block.timestamp >= genesisTimestamp + 365 days,
                "BCA: secondary market locked (365-day genesis period)");
        if (!secondaryMarketOpen &&
            block.timestamp >= genesisTimestamp + 365 days) {
            secondaryMarketOpen = true;
        }
        _;
    }

    // =========================================================
    // CONSTRUCTOR — GENESIS
    // =========================================================

    constructor() {
        genesisDeployer    = msg.sender;
        governanceAddress  = msg.sender; // em produção: endereço multisig do BRICS
        genesisTimestamp   = block.timestamp;

        // F_0 = 1.0 (base 2001, normalizado)
        Ft          = PRECISION;
        FtPrevious  = PRECISION;
        FtAtGenesis = PRECISION;

        // -------------------------------------------------------
        // GENESIS — 5 membros BRICS originais
        // Pesos λ=0.5 renormalizados (basis points de 10000)
        // conforme Tabela 3 do paper e Tabela I1 do Resumo Executivo
        //
        // PRODUÇÃO: substituir msg.sender pelos endereços reais
        // de cada Banco Central membro antes do deploy.
        // -------------------------------------------------------
        _addMember("Brasil",        "BR", 2130, msg.sender); // 21.3%
        _addMember("Russia",        "RU", 1590, msg.sender); // 15.9%
        _addMember("India",         "IN", 2000, msg.sender); // 20.0%
        _addMember("China",         "CN", 3320, msg.sender); // 33.2%
        _addMember("Africa do Sul", "ZA",  960, msg.sender); //  9.6%
        // Soma = 10000 bps = 100% ✓

        // Supply genesis S_0 = 2.799 bilhões de tokens
        // proporcional ao PIB do bloco em 2001 (Tabela I1)
        uint256 genesisAmount = 2_799_000_000 * PRECISION;
        genesisSupply = genesisAmount;
        _totalSupply  = genesisAmount;

        // -------------------------------------------------------
        // DISTRIBUIÇÃO GENESIS — proporcional ao peso λ de cada membro
        // Cada BC recebe sua cota no momento do genesis
        // Brasil:        21.3% → 596,187,000 BCA
        // Rússia:        15.9% → 444,841,000 BCA
        // Índia:         20.0% → 559,800,000 BCA
        // China:         33.2% → 929,268,000 BCA
        // África do Sul:  9.6% → 268,704,000 BCA
        // -------------------------------------------------------
        uint256 distributed = 0;
        for (uint i = 0; i < memberCodes.length; i++) {
            Member storage m = members[memberCodes[i]];
            uint256 memberShare;

            // Último membro recebe o restante para evitar arredondamento
            if (i == memberCodes.length - 1) {
                memberShare = genesisAmount - distributed;
            } else {
                memberShare = (genesisAmount * m.gdpWeight) / BPS_BASE;
            }

            _balances[m.bcAddress] += memberShare;
            distributed            += memberShare;
            emit Transfer(address(0), m.bcAddress, memberShare);
        }

        genesisComplete    = true;
        secondaryMarketOpen = false;
        lastMintTimestamp  = block.timestamp;
        lastFtUpdate       = block.timestamp;

        emit FundamentalUpdated(Ft, block.timestamp);
    }

    // =========================================================
    // ERC-20 PADRÃO
    // =========================================================

    function name()        public pure returns (string memory) { return NAME; }
    function symbol()      public pure returns (string memory) { return SYMBOL; }
    function decimals()    public pure returns (uint8)         { return DECIMALS; }
    function totalSupply() public view override returns (uint256) { return _totalSupply; }

    function balanceOf(address account)
        public view override returns (uint256)
    {
        return _balances[account];
    }

    function transfer(address to, uint256 amount)
        public override marketOpen returns (bool)
    {
        _transfer(msg.sender, to, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount)
        public override marketOpen returns (bool)
    {
        uint256 currentAllowance = _allowances[from][msg.sender];
        require(currentAllowance >= amount, "BCA: insufficient allowance");
        unchecked { _allowances[from][msg.sender] = currentAllowance - amount; }
        _transfer(from, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount)
        public override returns (bool)
    {
        _allowances[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function allowance(address owner, address spender)
        public view returns (uint256)
    {
        return _allowances[owner][spender];
    }

    // =========================================================
    // CLEARING — LIQUIDAÇÃO INTRA-BLOCO (Seção 6)
    // =========================================================

    /**
     * @notice Liquida comércio intra-bloco entre dois membros
     * @param to         Endereço do BC destinatário
     * @param amount     Valor em tokens BCA
     * @param fromCode   Código do membro exportador (ex: "BR")
     * @param toCode     Código do membro importador (ex: "IN")
     *
     * Fluxo: BC Brasil debita Reais → adquire BCA → transfere ao BC Índia
     * → BC Índia converte em Rupias. Fee τ retido pelo protocolo.
     */
    function settleClearing(
        address to,
        uint256 amount,
        string calldata fromCode,
        string calldata toCode
    ) external returns (bool) {
        require(amount > 0, "BCA: amount must be > 0");
        require(members[fromCode].active, "BCA: from member not active");
        require(members[toCode].active,   "BCA: to member not active");
        require(_balances[msg.sender] >= amount, "BCA: insufficient balance");

        // Calcula taxa de protocolo τ = 2% (Seção 5.3)
        uint256 fee    = (amount * TAU_BPS) / BPS_BASE;
        uint256 netAmt = amount - fee;

        // Transfere valor líquido ao destinatário
        _balances[msg.sender] -= amount;
        _balances[to]         += netAmt;

        // Taxa τ vai para governança do bloco (Seção 5.3)
        // A governança administra e distribui conforme necessidade
        _balances[governanceAddress] += fee;
        emit Transfer(msg.sender, governanceAddress, fee);
        emit GovernanceFundsReceived("CLEARING_FEE", fee, block.timestamp);

        // Atualiza mini-PIB de ambos os membros (Apêndice A.4)
        // "Cada transação incrementa o mini-PIB dos dois lados simultaneamente"
        members[fromCode].miniPIB += amount;
        members[toCode].miniPIB   += amount;
        totalMiniPIB              += amount * 2;

        // Registra no histórico (equivalente ao PoE on-chain)
        clearingHistory.push(ClearingTx({
            from:        msg.sender,
            to:          to,
            amount:      netAmt,
            feeCollected: fee,
            timestamp:   block.timestamp,
            fromMember:  fromCode,
            toMember:    toCode
        }));

        emit Transfer(msg.sender, to, netAmt);
        emit Transfer(msg.sender, address(this), fee);
        emit ClearingSettled(
            msg.sender, to, netAmt, fee,
            fromCode, toCode, block.timestamp
        );

        // Verifica se mini-PIB atingiu nova máxima → Mint 1
        if (totalMiniPIB > miniPIBHighWaterMark) {
            _executeMint1();
        }

        return true;
    }

    // =========================================================
    // MINT/BURN — REGRA DE TRÊS REGIMES (Seção 5.2, Tabela 4)
    // =========================================================

    /**
     * Mint 1 — Crescimento real (Apêndice A.4)
     * Ativado quando mini-PIB total supera máxima histórica.
     * Tokens mintados vão para a RESERVA DO PROTOCOLO — ficam disponíveis
     * para defesa do corredor via corridorAsk.
     * O valor recebido pelas vendas do corredor vai para governança.
     */
    function _executeMint1() internal {
        if (miniPIBHighWaterMark == 0) {
            miniPIBHighWaterMark = totalMiniPIB;
            return;
        }

        uint256 increment  = totalMiniPIB - miniPIBHighWaterMark;
        uint256 mintAmount = (_totalSupply * MINT_FRACTION * increment) /
                             (BPS_BASE * miniPIBHighWaterMark);

        // Aplica CAP mensal (Seção 5.2)
        uint256 cap = (_totalSupply * CAP_BPS) / BPS_BASE;
        if (mintAmount > cap) mintAmount = cap;

        if (mintAmount > 0) {
            miniPIBHighWaterMark = totalMiniPIB;
            // Tokens ficam no contrato para defesa do corredor
            _mint(address(this), mintAmount);
            protocolReserve += mintAmount;
            emit MintExecuted("MINT_1_REAL_GROWTH", mintAmount, _totalSupply);
        }
    }

    /**
     * Mint 2 — Recapitalização do corredor (Apêndice A.4)
     * Ativado quando reserva do protocolo chega a zero.
     * Mesmo princípio: tokens vão para reserva do protocolo.
     * Quando o corredor vende esses tokens, o ETH vai para governança.
     * O bloco BRICS tem despesas operacionais reais — a governança
     * administra esses recursos.
     */
    function _executeMint2() internal {
        uint256 mintAmount = (genesisSupply * MINT_FRACTION) / BPS_BASE;
        // Tokens ficam no contrato para defesa do corredor
        _mint(address(this), mintAmount);
        protocolReserve += mintAmount;
        emit MintExecuted("MINT_2_CORRIDOR_RECAPITALIZATION", mintAmount, _totalSupply);
    }

    /**
     * Burn — Regime de crise (Seção 5.2, Tabela 4)
     * Condição AND: ĝ_t < -2σ E P/F < (1-δ)
     * Dupla confirmação para evitar falsos positivos
     */
    function executeBurn(uint256 currentPrice) external onlyMemberBC {
        // Verifica condição de estresse de preço P/F < (1-δ)
        uint256 lowerBound = (Ft * (BPS_BASE - DELTA_BPS)) / BPS_BASE;
        require(currentPrice < lowerBound,
                "BCA: price not in stress zone — burn not justified");

        // Verifica que não é especulação transitória (simplificado no protótipo)
        // Em produção: ĝ_t < -2σ seria calculado via oracle de volume
        uint256 burnAmount = (_totalSupply * BURN_CAP_BPS) / BPS_BASE;

        // Burn só da reserva do protocolo — não dos membros
        require(protocolReserve >= burnAmount,
                "BCA: insufficient reserve for burn");

        protocolReserve -= burnAmount;
        _burn(address(this), burnAmount);

        emit BurnExecuted(burnAmount, _totalSupply);
    }

    // =========================================================
    // CORREDOR DE ARBITRAGEM δ (Seção 6.4)
    // =========================================================

    /**
     * @notice Bid — protocolo adquire tokens a F_t × (1-δ)
     * Árbitro traz tokens de volta ao corredor quando P < F_t×(1-δ)
     */
    function corridorBid(uint256 tokenAmount) external marketOpen {
        uint256 bidPrice = (Ft * (BPS_BASE - DELTA_BPS)) / BPS_BASE;
        uint256 ethEquivalent = (tokenAmount * bidPrice) / PRECISION;

        require(_balances[msg.sender] >= tokenAmount,
                "BCA: insufficient token balance");
        require(protocolReserve >= ethEquivalent,
                "BCA: reserve insufficient for bid");

        _balances[msg.sender]  -= tokenAmount;
        _balances[address(this)] += tokenAmount;
        protocolReserve        -= ethEquivalent;

        // Devolve ETH equivalente ao árbitro
        (bool sent,) = msg.sender.call{value: ethEquivalent}("");
        require(sent, "BCA: ETH transfer failed");

        emit CorridorIntervention("BID", bidPrice, Ft, tokenAmount);
    }

    /**
     * @notice Ask — protocolo emite tokens a F_t × (1+δ)
     * Árbitro compra tokens quando P > F_t×(1+δ).
     * ETH recebido vai para a GOVERNANÇA DO BLOCO — não fica no contrato.
     * A governança administra esses recursos para despesas do BRICS.
     */
    function corridorAsk() external payable marketOpen {
        uint256 askPrice   = (Ft * (BPS_BASE + DELTA_BPS)) / BPS_BASE;
        uint256 tokenAmount = (msg.value * PRECISION) / askPrice;

        require(tokenAmount > 0, "BCA: insufficient ETH sent");
        require(protocolReserve >= tokenAmount, "BCA: reserve insufficient for ask");

        // Debita da reserva de tokens
        protocolReserve -= tokenAmount;

        // Transfere tokens da reserva do contrato para o comprador
        _balances[address(this)] -= tokenAmount;
        _balances[msg.sender]    += tokenAmount;
        emit Transfer(address(this), msg.sender, tokenAmount);

        // ETH vai para governança do bloco
        (bool sent,) = governanceAddress.call{value: msg.value}("");
        require(sent, "BCA: governance transfer failed");

        emit GovernanceFundsReceived("CORRIDOR_ASK", msg.value, block.timestamp);
        emit CorridorIntervention("ASK", askPrice, Ft, tokenAmount);

        // Verifica se reserva zerou → Mint 2
        if (protocolReserve == 0) {
            _executeMint2();
        }
    }

    // =========================================================
    // ATUALIZAÇÃO DO FUNDAMENTAL F_t (Seção 3)
    // =========================================================

    /**
     * @notice Atualiza F_t com novo crescimento agregado do bloco
     * @param growthBPS Crescimento do bloco em basis points
     *                  (ex: 571 = 5.71% crescimento médio 2001-2024)
     *
     * Em produção: calculado automaticamente via oracle WDI/IMF
     * No protótipo: atualizado por governança dos BCs membros
     *
     * F_{t+1} = F_t × (1 + g_agregado) — Seção 3.1
     */
    function updateFundamental(uint256 growthBPS)
        external onlyMemberBC
    {
        require(growthBPS <= 3000, "BCA: growth > 30% implausible");

        FtPrevious = Ft;
        Ft = (Ft * (BPS_BASE + growthBPS)) / BPS_BASE;
        lastFtUpdate = block.timestamp;

        emit FundamentalUpdated(Ft, block.timestamp);
    }

    // =========================================================
    // FUNÇÕES DE LEITURA — ESTADO DO PROTOCOLO
    // =========================================================

    /**
     * @notice Retorna o estado completo do protocolo para auditoria
     * "Não há relatório especial a ser gerado — o ledger público é o relatório" (Seção 6.10)
     */
    function getProtocolState() external view returns (
        uint256 currentFt,
        uint256 previousFt,
        uint256 supply,
        uint256 reserve,
        uint256 miniPIBTotal,
        uint256 highWaterMark,
        bool    marketIsOpen,
        uint256 upperCorridor,
        uint256 lowerCorridor
    ) {
        return (
            Ft,
            FtPrevious,
            _totalSupply,
            protocolReserve,
            totalMiniPIB,
            miniPIBHighWaterMark,
            secondaryMarketOpen || block.timestamp >= genesisTimestamp + 365 days,
            (Ft * (BPS_BASE + DELTA_BPS)) / BPS_BASE,
            (Ft * (BPS_BASE - DELTA_BPS)) / BPS_BASE
        );
    }

    function getMemberState(string calldata code) external view returns (
        string memory memberName,
        uint256 weight,
        uint256 miniPIBValue,
        address bcAddr,
        bool    isActive
    ) {
        Member storage m = members[code];
        return (m.name, m.gdpWeight, m.miniPIB, m.bcAddress, m.active);
    }

    function getClearingHistoryLength() external view returns (uint256) {
        return clearingHistory.length;
    }

    function getHHI() external view returns (uint256 hhi) {
        // HHI = Σ w_i² (Seção 4)
        // Retorna em basis points²
        hhi = 0;
        for (uint i = 0; i < memberCodes.length; i++) {
            uint256 w = members[memberCodes[i]].gdpWeight;
            hhi += (w * w) / BPS_BASE;
        }
    }

    // =========================================================
    // FUNÇÕES INTERNAS
    // =========================================================

    function _addMember(
        string memory memberName,
        string memory code,
        uint256 weight,
        address bcAddr
    ) internal {
        members[code] = Member({
            name:      memberName,
            code:      code,
            gdpWeight: weight,
            miniPIB:   0,
            bcAddress: bcAddr,
            active:    true
        });
        memberCodes.push(code);
        memberCount++;
        emit MemberAdded(code, weight);
    }

    function _transfer(address from, address to, uint256 amount) internal {
        require(from != address(0), "BCA: transfer from zero address");
        require(to   != address(0), "BCA: transfer to zero address");
        require(_balances[from] >= amount, "BCA: insufficient balance");

        unchecked {
            _balances[from] -= amount;
            _balances[to]   += amount;
        }
        emit Transfer(from, to, amount);
    }

    function _mint(address to, uint256 amount) internal {
        require(to != address(0), "BCA: mint to zero address");
        _totalSupply    += amount;
        _balances[to]   += amount;
        emit Transfer(address(0), to, amount);
    }

    function _burn(address from, uint256 amount) internal {
        require(_balances[from] >= amount, "BCA: burn exceeds balance");
        unchecked {
            _balances[from] -= amount;
            _totalSupply    -= amount;
        }
        emit Transfer(from, address(0), amount);
    }

    /**
     * @notice Atualiza endereço de governança (requer votação 2/3)
     * Em produção: substituir por votação on-chain dos membros
     */
    function updateGovernanceAddress(address newAddress)
        external onlyMemberBC
    {
        require(newAddress != address(0), "BCA: zero address");
        governanceAddress = newAddress;
        emit GovernanceAddressUpdated(newAddress);
    }

    // ETH enviado diretamente também vai para governança
    receive() external payable {
        if (msg.value > 0 && governanceAddress != address(0)) {
            (bool sent,) = governanceAddress.call{value: msg.value}("");
            if (sent) {
                emit GovernanceFundsReceived("DIRECT_DEPOSIT", msg.value, block.timestamp);
            }
        }
    }
}
