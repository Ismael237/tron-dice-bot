from hypothesis import given, strategies as st

from services.fairness_service import FairnessService as FS


@given(
    server_seed=st.text(min_size=64, max_size=64, alphabet=st.characters(min_codepoint=48, max_codepoint=102)).map(lambda s: "a" * 64),
    client_seed=st.text(min_size=1, max_size=16),
    nonce=st.integers(min_value=0, max_value=1_000_000),
)
def test_roll_determinism(server_seed, client_seed, nonce):
    # For fixed inputs, result must be deterministic
    r1 = FS.roll_dice(server_seed, client_seed, nonce)
    r2 = FS.roll_dice(server_seed, client_seed, nonce)
    assert r1.result_number == r2.result_number
    assert r1.hex_substring == r2.hex_substring
    assert r1.decimal_result == r2.decimal_result


@given(
    server_seed=st.just("b" * 64),
    client_seed=st.text(min_size=1, max_size=16),
    nonce=st.integers(min_value=0, max_value=1_000_000),
)
def test_roll_bounds_1_100(server_seed, client_seed, nonce):
    r = FS.roll_dice(server_seed, client_seed, nonce)
    assert 1 <= r.result_number <= 100


@given(n=st.integers(min_value=1, max_value=100))
def test_multiplier_monotonicity(n):
    # As target N increases (harder to win), multiplier should not increase when going the other way.
    # We'll compare N and N+1 (when possible): m(N+1) >= m(N)
    m_n = FS.calculate_multiplier(n)
    if n < 100:
        m_next = FS.calculate_multiplier(n + 1)
        assert m_next >= m_n


def test_verify_consistency_simple(user_factory):
    # Create a valid user using the fixture (ensures required fields)
    u = user_factory(telegram_id="u1", username="u1")

    # Ensure seed and roll
    seed = FS.ensure_active_seed(u.id, client_seed="cs")
    from database.database import get_db_session

    with get_db_session() as s:
        seed = s.query(type(seed)).get(seed.id)
        nonce = FS._increment_nonce(s, seed)
        roll = FS.roll_dice(seed.server_seed, seed.client_seed, nonce)
        game_hash = FS.compute_game_hash(seed.server_seed_hash, seed.client_seed, nonce)

    v = FS.verify_game_fields(
        server_seed=seed.server_seed,
        client_seed=seed.client_seed,
        nonce=nonce,
        expected_result_number=roll.result_number,
        expected_game_hash=game_hash,
    )
    assert v["ok"] is True
